# V2 Exp 2 — Deterministic rules baseline (semantic edition, round 3)

Notebook: `notebooks/v2/exp02_rules_baseline.ipynb`. Code: `src/rules.py` (2a), `src/rules_v2.py` (2b, frozen), `src/rules_text.py` (2c, regex parsing; directory lookup added in round 3), `src/metrics_ext.py`. Results: `results/v2/development/exp02_rules/`. Archives of earlier editions: `results/v2_easy_archive/`, `results/v2_semantic_r1_archive/`, `results/v2_semantic_r2_archive/`. No LLM, cost $0.

**Hypothesis:** once decision-critical facts live only in free-text notes, rules reading structured fields fail, and each hardening round lowers what regex parsing can recover.

| System | Dev (70) | Validation (30, unseen) | Dev false approvals |
|---|---|---|---|
| 2a existing rules | 22/70 = 31% | 12/30 = 40% | 39/52 |
| 2b V2 rules, frozen (easy V2: 70/70, 30/30) | 34/70 = 49% (37-60%) | 14/30 = 47% (30-64%) | 15/52 |
| 2c rules + regex parsing | 48/70 = 69% (57-78%) | 21/30 = 70% (52-83%) | 6/52 |

Progression of 2c dev/validation: round 1 65/70 and 25/30; round 2 54/70 and 23/30; round 3 48/70 and 21/30.

**Findings:** the frozen rules halve once facts leave structured fields. Each hardening round (computed facts and noise; dictated and local-language notes and coarse bill category) lowers the parser. Self-contained claims are now hardest (2/8 on validation), workflow claims still parse (15/16). 2a now approves almost everything (its category checks no longer fire). The 2c parser is a frozen baseline and could be extended for the new phrasing; validation is 30 claims, so intervals are wide. Notes are LLM-drafted, automatically validated only; 6 are mainly in Japanese or Hinglish (fewer than planned).

**Decision:** deterministic bar = 2c at ~70% (validation), 4/22 false approvals, $0. Further hardening has diminishing returns; next Exp 3 (generic LLM, no policy).
