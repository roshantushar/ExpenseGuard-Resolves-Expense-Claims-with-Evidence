"""Evaluator-side retrieval metrics (reads ground-truth required clauses, so never import from runtime code)."""
from __future__ import annotations
import math
from .retrievers import REGION


def score(case: dict, req: set, chunks: list, hits: list, k: int) -> dict:
    ch = [chunks[i] for i, _ in hits]
    rel = [bool(req & set(x["clause_ids"])) for x in ch]
    cov = set().union(*[set(x["clause_ids"]) for x in ch]) if ch else set()
    n_rel_total = sum(bool(req & set(c["clause_ids"])) for c in chunks)
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rel))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(k, n_rel_total)))
    d, reg = case["transaction_date"], REGION.get(case["bill"]["country"], "")
    return {"recall": len(req & cov) / len(req), "precision": sum(rel) / k, "rr": next((1 / (r + 1) for r, x in enumerate(rel) if x), 0.0),
            "ndcg": dcg / idcg if idcg else 0.0, "full": req <= cov, "ctx_words": sum(len(x["text"].split()) for x in ch),
            "n_retrieved": len(ch),
            "wrong_year_chunks": sum(x["category"] == "general" and not (x["effective_from"] <= d <= x["effective_to"]) for x in ch),
            "wrong_region_chunks": sum(x["region"] not in ("GLOBAL", reg) for x in ch),
            "retrieved": [x["chunk_id"] for x in ch]}
