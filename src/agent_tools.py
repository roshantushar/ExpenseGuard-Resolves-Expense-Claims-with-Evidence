"""V3: agentic-RAG tools for src/agent.py's ReAct loop. Two additions to Exp 17's typed enterprise
tools, both read-only:

  search_policy_corpus  -- the frozen M4 retriever (Exp 9: voyage-4-lite, 600/100 chunking, K=8) exposed
                            as a callable tool instead of being fetched once before the loop starts, so
                            the agent decides what to search and can re-query after a turn's observation
                            points it somewhere new (e.g. a clause that names a second clause to look up).
  check_rate_ceiling    -- a deterministic calculator (amount, nights, ceiling in) -> nightly rate and
                            compliant flag, so the model is never asked to do the division/comparison
                            itself (the same reasoning-bias Exp 33 found: models mishandling arithmetic
                            they were already handed).

record_decision is not a lookup: src/agent.py treats it as the loop's one terminal action, defined
there alongside the loop rather than here.

Both tools are visible-only: search_policy_corpus takes only what the agent itself supplies (a query,
and optionally a document category/region/date to narrow it) plus the claim's own transaction_date and
country as defaults when the agent doesn't specify -- never a label, case_family or ground-truth field.
"""
from __future__ import annotations
from . import retrieval, retrievers

EMB, CFG, K_DEFAULT = "voyageai/voyage-4-lite", "fixed600_100", 8
CROSSCUT = {"general", "approval", "exceptions", "controls", "fx", "circular", "regional"}
NONBINDING = {"historical", "faq"}
CATEGORIES = sorted({"travel", "transport", "training", "meals", "software", "telecom", "gifts", "card"} | CROSSCUT | NONBINDING)
_retriever = None


def _R():
    global _retriever
    if _retriever is None:
        _retriever = retrievers.Retriever(EMB, CFG)
    return _retriever


def make_search_policy_corpus(case: dict):
    """Returns a search_policy_corpus(query, doc_category=None, region=None) closure bound to this
    case's own transaction_date and country (used only as defaults, never forced) -- so each agent run
    gets its own tool instance rather than a global one leaking state between cases."""
    default_date = case["transaction_date"]
    default_region = retrievers.REGION.get(case["bill"]["country"], "")

    def search_policy_corpus(query: str, doc_category: str = None, region: str = None) -> dict:
        R = _R()
        d = default_date
        reg = (region or default_region or "").upper() or default_region
        allowed_cat = {doc_category} if doc_category else None
        mask = []
        for x in R.chunks:
            if not (x["effective_from"] <= d <= x["effective_to"]):
                mask.append(False); continue
            if x["region"] not in ("GLOBAL", reg):
                mask.append(False); continue
            if allowed_cat is not None and x["category"] not in allowed_cat and x["category"] not in CROSSCUT:
                mask.append(False); continue
            mask.append(True)
        import numpy as np
        from . import embed
        qv = embed.embed(EMB, [query], tag="AGENT_SEARCH")[0]
        ranked = R.rank("dense", "unused", qv, K_DEFAULT, np.array(mask))
        ctx = R.context(ranked)
        return {"ok": True, "found": bool(ranked), "data": {"excerpts": ctx, "n_chunks": len(ranked)}, "error": None}

    return search_policy_corpus


def check_rate_ceiling(amount: float, nights: int, ceiling: float) -> dict:
    """Deterministic calculator: nightly rate = amount / nights, compliant iff rate <= ceiling.
    Exists so the agent looks up the ceiling (via search_policy_corpus / enterprise tools) but never
    has to do the division or comparison itself."""
    if not nights or nights <= 0:
        return {"ok": False, "found": False, "data": None, "error": "nights must be a positive number"}
    rate = round(float(amount) / float(nights), 2)
    return {"ok": True, "found": True, "data": {"nightly_rate": rate, "ceiling": ceiling, "compliant": rate <= float(ceiling) + 1e-9, "over_by": round(max(0.0, rate - float(ceiling)), 2)}, "error": None}


AGENT_TOOL_SPECS = {
    "search_policy_corpus": ({"query": ("str", None), "doc_category": ("str?", None), "region": ("str?", None)},
                              "Search the policy corpus by meaning. doc_category narrows to one document category "
                              f"(one of: {', '.join(CATEGORIES)}) when you already know which kind of rule you need; region narrows to a "
                              "regional addendum (SG/IN/JP) plus global documents. Omit either to search broadly. Call again with a "
                              "different query/category if an excerpt you retrieved names another clause or exception you have not yet looked up."),
    "check_rate_ceiling": ({"amount": ("amount", None), "nights": ("amount", None), "ceiling": ("amount", None)},
                            "Given the total accommodation charge, the number of nights, and a ceiling value you already found, returns the "
                            "computed nightly rate and whether it is within the ceiling. Use this instead of doing the division yourself."),
}
