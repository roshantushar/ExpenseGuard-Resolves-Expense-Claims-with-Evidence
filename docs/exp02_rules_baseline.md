# Experiment 2 — Deterministic rules baseline

**Question:** How much of expense compliance can ordinary deterministic code solve?
**Code:** `src/rules.py`, `scripts/exp02_rules.py`, `src/evaluate.py` · **Outputs:** `results/development/exp02/`, `results/plots/exp02_rules_development.png` · **Cost:** $0, no LLM.

## Configuration (frozen)
Rules read only the claim plus static tables: frozen FX, employee grade, exact-duplicate history (same bill number, or same employee + merchant + date + amount) and manager-approval records. Policy constants (meal ceilings, hotel ceilings, submission windows, approval thresholds) are transcribed from the policy corpus. Checks, in order: mandatory fields → exact duplicate → submission window by year → personal/consumer spend → unitemised mixed bill → restaurant (alcohol, attendee count, per-person ceiling, description/bill conflict) → ride-hail route → generic supplies wording → hotel ceiling → SGD approval thresholds (500 / 5000).
Not in the baseline: near-duplicate and split-transaction detection, travel/exception/conference lookups, and any reading of free text beyond regex.

The rules were written from the policy text and by viewing the development *claims*; ground-truth labels were not viewed while writing them, and no tuning was done afterwards. The result below is the first run.

## Results — development (n = 60)
| Metric | Value |
|---|---|
| Correct Disposition Rate | **47/60 = 78.3%** (Wilson 95%: 66.4–86.9%) |
| False Approval Rate | 5/39 = 12.8% (above the 10% guardrail) |
| Human Review Rate | 15.0% (9 escalations predicted; 8 unnecessary, 4 missed) |
| Missing-field exact match | 5/15 (see below) |
| Median latency | 0.02 ms, cost $0, tokens 0 |

Accuracy by family: self-contained 13/13, temporal 3/3, regional 5/5, evidence conflict 2/2, missing information 10/10, duplicates 7/7, split transaction 3/5, fixed workflow 3/8, dynamic agent 1/7.

## Findings
1. **Rules solve everything that needs only the claim and arithmetic.** Per-person ceilings, year-specific limits, regional overrides and exact duplicates are all correct. This beats the gpt-4o-mini and Llama results in Exp 1, whose 10 cases were mostly of this kind. Later systems must beat this line.
2. **Rules cannot solve external-evidence cases.** All 13 errors are split-transaction (2), fixed-workflow (5) and dynamic-agent (6) cases, which need travel, exception, conference or prior-expense evidence. The hotel rule escalated every over-ceiling claim, which is safe but unnecessary (8 over-escalations).
3. **Four false approvals were ESCALATE cases the rules missed** (split purchases, a software subscription and one hotel case). These are the risky failures.
4. **Missing-field names:** the decision was right in 14/15 cases but the field names matched exactly in only 5/15. Field vocabulary (for example `external_attendee_names`) is not defined anywhere in the task, so this metric is partly a naming problem. Exp 13 should score against a fixed vocabulary or semantic match.

## Caveats
- The dataset is templated (58 distinct claim texts in 120 cases), so 100% on template-driven families may not carry to validation and final test. Validation has not been run.
- Regexes for attendee counts are brittle and cover only the wording seen in development.

## Decision
Baseline recorded. Rules are strong on self-contained cases and blind to enterprise evidence, which matches the plan's architecture ladder. Next: Exp 3 (generic LLM without policy) and Exp 4 (full-policy long context).

## Addendum: validation run (added later)
The same rules run on the 20 validation cases (free, run after the fact): 16/20 correct (80%), 2 false approvals, 20% human review. Family results: all claim-only families 100%, fixed-workflow 1/2, dynamic 2/3, split 0/2. No rules were changed after the development run.
