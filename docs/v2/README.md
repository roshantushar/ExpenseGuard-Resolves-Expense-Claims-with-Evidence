# ExpenseGuard V2 — master index

## The problem

An employee submits an expense claim: a bill, a free-text note explaining it, nothing else structured.
The system has to decide **APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE**, using:
- a **22-document policy corpus** (global rules, regional addenda, category policies, finance circulars,
  exception procedures),
- **11 enterprise tables** (approvals, delegations, travel requests, project/budget status, prior
  expenses),
- and the note itself — deliberately hardened across three rounds so decision-critical facts (nights,
  attendee counts, exception references, even the expense category) live only in prose, sometimes next
  to a distractor sentence that states something else.

The question this whole project answers: **what architecture gets this right, safely, and why does
everything that looks like it should work often not?**

## What's in this folder
One `.md` file per experiment (hypothesis → method → result → decision), a notebook or script backing
almost every one, and every number traceable to a file under `results/v2/`. Nothing here is hand-typed.
No git commit/push has been made on the user's behalf.

## Governance & security alignment

Framed against recognized frameworks — this is an honest mapping of what was actually built and
adversarially tested to the risk categories they name, not a compliance certification.

- **OWASP Top 10 for LLM Applications — LLM06: Excessive Agency.** Directly and concretely mitigated:
  every tool is read-only, bounded by a step cap and call deduplication (Exp 20, 28), and — the core
  mechanism — Exp 41's disposition gate structurally prevents the model from overriding a tool that
  already computed the correct answer, with Exp 43's domain guards restricting each tool to only the
  claim types it actually applies to.
- **OWASP Top 10 for LLM Applications — LLM01: Prompt Injection.** Identified and adversarially tested
  (Exp 28: injection, fake authority, malicious tool-embedded text), with a prompt-level defense in
  place (retrieved/user text is treated as data, never instructions). **Not fully solved**: Exp 28 found
  retrieval-text injection can still defeat that defense — this remains a documented, disclosed open
  risk, carried forward rather than silently fixed, per the project's own decision at the time.
- **Human oversight (in the spirit of Singapore's IMDA Model AI Governance Framework for agentic AI and
  the EU AI Act's human-oversight/transparency principles for workplace and financial systems).**
  ESCALATE is a first-class, deliberately safe outcome, not a failure — any claim the system can't
  resolve with confidence routes to a human reviewer by design. The frozen architecture (Exp 30) was
  chosen specifically because it drives false approvals to 0%, at the cost of some raw accuracy, over a
  design that was more "accurate" but approved bad claims 13.5% of the time.
- **Transparency and auditability.** Every decision's full evidence trail — retrieved clauses, resolved
  facts, every tool call — is logged and inspectable (`ui/`'s demo app is that transparency made
  visible). Ground truth is never read by runtime code, enforced by automated leakage tests
  (`tests/test_no_leakage.py`), so no decision path can see the answer it's being graded against.

## The two designs, and which one is actually running

| | Frozen & final-tested | Best validated |
|---|---|---|
| **What** | Selective resolver (Exp 30/32) | Guarded agent (Exp 40-52) |
| **Mechanism** | Deterministic rules → conclusive? code decides : single-shot LLM decides | Deterministic rules → conclusive? code decides : bounded ReAct agent with code-computed disposition tools |
| **Result** | 30/50 final test (60%), **0% FAR** | 44/70 dev (62.9%) **and** 21/30 validation (70.0%), **0% FAR on both** |
| **Status** | **This is what's shipped.** Tested once on the real held-out final test, hash-manifest-verified, never rerun. | Fully validated, beats the frozen design's own dev accuracy at matching safety — but never run against final test, no freeze manifest. |

**If asked "what does the system do," the honest answer is the selective resolver, exactly as frozen.**
The guarded agent is the better, proven candidate to replace it, pending a deliberate freeze decision.

## The flow, end to end

```
                         EMPLOYEE EXPENSE CLAIM
                    (bill + free-text note, nothing else)
                                  │
                                  ▼
                 ┌────────────────────────────────┐
                 │   DETERMINISTIC RESOLVER         │
                 │   rules_text.py parses the note  │
                 │   rules_v2.py applies policy      │
                 │   mechanics (visible-only,        │
                 │   never reads a label)            │
                 └────────────────┬─────────────────┘
                                  │
                     conclusive? ─┴─ (a rule fired, AND every
                                      needed field was extracted)
                    ┌─────yes───────────────no──────┐
                    ▼                                ▼
         ┌─────────────────────┐      ┌───────────────────────────────┐
         │  CODE DECIDES         │      │   RESIDUAL STEP (the part      │
         │  no LLM call, $0       │      │   every experiment below is    │
         │  100% accurate on      │      │   about)                       │
         │  unseen final-test     │      └───────────────┬────────────────┘
         │  data (Exp 32)         │                       │
         └───────────┬───────────┘         ┌──────────────┴───────────────┐
                     │                      ▼                              ▼
                     │           FROZEN DESIGN (Exp 30/32)      BEST VALIDATED DESIGN
                     │           M4 RAG + resolved facts        (Exp 40-52)
                     │           → single-shot LLM               bounded ReAct agent +
                     │           28.6% accurate                  guarded, argument-minimal
                     │                                           tools that compute the
                     │                                           disposition in CODE, gated
                     │                                           so the model can't override
                     │                                           a tool's correct answer
                     │                                           58-89% accurate, 0% FAR
                     │                      │                              │
                     └──────────────────────┴──────────────────────────────┘
                                             ▼
                              APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE
```

### How the diagnostic journey actually went (Exp 34 → 52)

```
Exp 34: rebuild as a full agent → WORSE than a fixed workflow (4/13 vs 7/13)
             │  Chennai hotel claim: used ceiling 14,500 instead of the correct 9,800
             ▼
   ┌─────────┴─────────┬─────────────┬──────────────┬───────────────┐
   ▼                    ▼             ▼              ▼               ▼
 Stricter          Stronger       Perfect RAG    Better RAG      Parallel
 prompt             model         handed          + forced        tool calls
 (35A)             (35B/46)       directly        re-query        (36)
   │                    │         (37, diag.)     (38 audit,       │
   ▼                    ▼             │            39 fix)         ▼
 FAR triples      16-30x cost,        ▼               │        more calls,
 same accuracy    same accuracy,  FAR quadruples       ▼        same accuracy,
                  FAR to 50%      → rules OUT      accuracy        worse step-
                                  evidence          FELL further   cap hits
                                  quality                          │
   └────────────────────┴──────────────┴────────────────┴─────────┘
                                        │
                    NONE of these fixed it. The model had the
                    right facts and still decided wrong, or
                    ignored a tool that already had the answer.
                                        ▼
              ┌─────────────────────────────────────────────┐
              │  THE FIX (Exp 40-41): give the model a tool   │
              │  that COMPUTES the disposition in code, and   │
              │  a gate that trusts the tool over the model    │
              └────────────────────┬────────────────────────┘
                                   ▼
                    7/13 → 9/13 → 11/13 → 17/19 (89.5%), one claim family
                                   ▼
              ┌─────────────────────────────────────────────┐
              │  Scale to the WHOLE dataset (Exp 45)          │
              │  accuracy UP, but FAR breaks (11.5%) in every  │
              │  category with no guarded tool                 │
              └────────────────────┬────────────────────────┘
                                   ▼
              ┌─────────────────────────────────────────────┐
              │  Exp 47-52: build the missing guards, one      │
              │  real bug at a time (7 found and fixed:        │
              │  clause conflicts, placeholder strings,         │
              │  date-arithmetic miscounts, a coarsened-        │
              │  category blind spot, a missing prerequisite    │
              │  check caught BY the validation run itself)     │
              └────────────────────┬────────────────────────┘
                                   ▼
                 44/70 dev (62.9%) AND 21/30 validation (70.0%)
                          0% false approvals on both
                 ── beats the frozen system's own dev number ──
```

## Full experiment index

### Part 1 — building the frozen architecture (Exp 0–33)
| # | Experiment | Headline result |
|---|---|---|
| 0 | Dataset validation + EDA | 0 critical errors; hardened 3x so facts live in free text |
| 1 | End-to-end sanity | *(stale — pre-hardening)* |
| 2 | Deterministic rules baseline | Regex-only rules collapse once facts move to free text |
| 3 | Generic LLM, no policy | Confident, unsupported answers |
| 4A/4B | Long-context feasibility/baseline | Feasible, $0.77/run, doesn't beat RAG |
| 5–10 | RAG tuning ladder | 600/100 chunking, K=8, dense, M4 metadata filter → Recall@8 0.56 |
| 11 | Policy oracle | Perfect retrieval only 22→25/70 — **reasoning, not retrieval, is the bottleneck** |
| 12, 12B | Hybrid rules + RAG; router probe | Motivated pulling mechanics into code; proved the routing concept |
| 13–17 | Component qualification | Missing-info, duplicates, enterprise facts, typed tools — each qualified |
| 18–20 | Workflow vs. agent | Workflow 64% beats a real agent (7/13, 30% FAR) → **agent gate closed** |
| 28 | Guardrail suite | Found & fixed a real bug; retrieval-injection logged as open risk |
| 29 | Abstention/escalation | Quantified risk-coverage behavior |
| **30** | **Architecture freeze** | **Selective resolver frozen**: 0% FAR, 61% dev |
| 31 | Cost-to-serve | $0.00043/claim — cost is a non-issue |
| **32** | **Frozen final test** | **30/50 (60%), 0% FAR** — *(dataset snapshot caveat: see the doc)* |
| 33 | Failure analysis | 20 errors: 9 reasoning, 5 over-asking, 4 fact gaps, 0 retrieval |

### Part 2 — the agentic-RAG diagnostic line (Exp 34–39): ruling things out
| # | Experiment | Result |
|---|---|---|
| 34 | Agentic RAG rebuild | Worse than the workflow: 4/13, tier-substitution false approval |
| 35 | Prompt / model / tool-interface isolated | None fixed it alone |
| 36 | Parallel turns + poka-yoke v2 | Bug fixed for its one target; step-cap hits got worse |
| 37 | Perfect policy oracle (diagnostic) | Same accuracy, FAR quadrupled — rules out evidence quality |
| 38 | $0 RAG trace audit | Agent's own queries: 33.6% recall, 0/13 ever re-queried |
| 39 | Fixed retrieval | Recall improved to 45.4% — **accuracy still fell** |

### Part 3 — the fix, and closing the gap (Exp 40–52)
| # | Experiment | Result |
|---|---|---|
| **40** | Decision-in-code | Ties the workflow: 7/13, 0% FAR |
| **41** | Disposition gate ($0) | Beats the workflow: 9/13, 0% FAR |
| 42 | + project-budget tool | Caught a tool firing on the wrong claim type, live |
| **43** | Guarded tools, corrected | 11/13 (84.6%) |
| **44** | Full confirmation | **17/19 (89.5%), 0% FAR** — 6/6 validation cases correct |
| 45 | Full-dataset extension | *(superseded)* accuracy up, FAR breaks to 11.5% |
| 46 | + stronger model | Still no: worse accuracy, 30x cost, FAR held at 0% by the guards |
| **47–52** | **Closing the gap** | 7 more real bugs found and fixed → **44/70 dev + 21/30 validation, 0% FAR on both** |

Full detail: `docs/v2/expNN_*.md`.

## Key findings, distilled
1. **RAG quality was never the dominant bottleneck** — perfect retrieval barely moves accuracy (Exp 11, 37).
2. **More autonomy made things worse, consistently** — looser prompts, bigger models, and parallel tool calls each either did nothing or made safety worse (Exp 35, 36, 46).
3. **The fix that worked: stop asking the model to decide, give it the answer.** Every point of accuracy gained from Exp 40 onward came from a tool computing the disposition in code, gated so the model can't override it.
4. **A tool is only safe to trust if its own inputs are reliable** — found and fixed at every level: the model's own reasoning (Exp 33), a poorly-scoped tool (Exp 42), and even a *reused, previously-tested* piece of code (`workflow_v2.decide()`, Exp 47) that turned out to share the same fragile free-text parsing it was meant to route around.
5. **Validation caught a real bug, and that's it working as intended** — the very first validation run (Exp 51→52) found a missing prerequisite check (`check_hotel_compliance` never verified there was an approved travel request). Fixed, re-verified, re-confirmed — exactly the discipline validation exists for.
6. **The dataset is not the problem.** The deterministic path scores 100% on unseen final-test data; every improvement this session came from fixing code, never from touching the data.

## Where things stand
- **Frozen and tested on the real final test:** Exp 30/32 — 30/50, 0% FAR. This is what's shipped.
- **Fully validated, not yet frozen:** the guarded-agent design (Exp 40-52) for the *entire* claim
  population — 44/70 dev, 21/30 validation, 0% FAR on both. Beats the frozen design's own dev number.
- **Not yet done:** a new freeze manifest and a one-shot run against the real final test. That is the
  next deliberate decision, not something to do implicitly.
- **Budget:** $4.36 of $5.00 spent (raised once this session from the original $3.50 cap).
