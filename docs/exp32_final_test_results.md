# Experiment 32 — Frozen final test results

**Run:** once, on the 40 final-test cases, after the freeze manifest was committed (`experiments/exp32_freeze_manifest.yaml`, 18 files hash-verified before the run). No code, prompt, threshold or model setting was changed after seeing these results.
**Outputs:** `results/final/exp32/` (predictions, per-case evaluation, `report.json`), `results/plots/exp32_final.png`. Cost of the run: $0.0105 (gpt-4o-mini); total project spend $0.258 of the $3.50 cap.

## Primary result: rules + fixed tool workflow (router), no LLM, no agent
| Metric | Value |
|---|---|
| **Correct Disposition Rate** | **38 / 40 = 95.0%** (95% Wilson interval 83.5–98.6%) |
| False approvals | 2 / 35 non-approvable = 5.7% (guardrail: under 10%) |
| Human Review Rate | 7.5% (3 of 40 escalated; 1 escalation missed, 0 unnecessary) |
| Median / P95 latency | 0.07 ms / 0.30 ms |
| Model cost per case | $0 |
| Challenge set (10 independently worded cases) | **9 / 10** (59.6–98.2%) |
| Currency-flagged cases (4, flagged from inputs before the run) | 2 / 4 |
| Excluding the 4 flagged cases | **36 / 36** (90.4–100%) |

## All systems run once on the final test
| System | Correct | Wilson 95% | False approvals | Human review | Challenge | Excl. flagged | Median latency | Cost per case |
|---|---|---|---|---|---|---|---|---|
| **router (frozen system)** | **38/40 (95.0%)** | 83.5–98.6% | 2/35 | 7.5% | 9/10 | 36/36 | 0.07 ms | $0 |
| rules only | 31/40 (77.5%) | 62.5–87.7% | 4/35 | 17.5% | 7/10 | 30/36 | 0.02 ms | $0 |
| gpt-4o-mini RAG + code facts | 25/40 (62.5%) | 47.0–75.8% | 1/35 | 0% | 5/10 | 24/36 | 1.68 s | $0.00026 |
| llama3.2:3b RAG + code facts | 10/40 (25.0%) | 14.2–40.2% | 17/35 (48.6%) | 0% | 4/10 | 9/36 | 3.11 s | $0 |

gpt-4o-mini used 58.5k input and 2.8k output tokens across the 40 cases. By family, the router got 4/4 evidence-conflict, 6/6 self-contained, 3/3 temporal, 2/2 regional, 7/7 missing-information, 5/5 duplicate, 2/3 split, 4/5 fixed-workflow and 5/5 dynamic cases.

## What this does and does not show
- The router scored highest on this benchmark, at zero model cost and sub-millisecond latency. Its interval (83.5–98.6%) does not overlap either LLM's (47.0–75.8% and 14.2–40.2%), so the gap to the LLMs is clear. It does overlap the rules-only interval (62.5–87.7%), so router versus rules alone is suggestive, not conclusive, at n = 40.
- The 4 currency-flagged cases account for both router errors. This is a labelling inconsistency, not a fitted result: the flag was defined and committed before the run.
- The benchmark is synthetic and templated (58 distinct claim texts among 120 cases), and much of the workflow was designed while looking at development and validation cases. These numbers estimate performance on this benchmark's final split, not real-world accuracy.
- The hotel branch that the workflow ESCALATEs was changed after seeing three dev/val labels (disclosed in the manifest). It did not need further changes on the final test.
