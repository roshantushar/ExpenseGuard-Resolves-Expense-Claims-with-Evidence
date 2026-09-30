# Exp 36 — ReAct Agent v2: parallel-turn loop + poka-yoke v2 tool interface

Named Exp 36 (not 35) to avoid overwriting Exp 35's already-recorded prompt/model/tool-interface
isolation results (`docs/exp35_isolate_fix.md`). Code: `src/agent_variants.py` (`run_parallel`,
`check_hotel_ceiling`, `SYSTEM_36`). Results: `results/current/development/exp36_parallel_pokayoke/`. Same
13 `C_AGENT_DYNAMIC` development claims as Exp 18/19/20/34/35.

**Two targeted upgrades over Exp 34's agent, both changed together (this is a combined redesign, not a
third isolated variable):**
1. **Parallel multi-tool turns.** The loop's JSON contract changed from one `{"tool", "args"}` per turn
   to `{"calls": [...]}` — a list of one or more independent tool calls executed within a single LLM
   round-trip, plus the existing call-deduplication. The step cap now bounds LLM round-trips, not
   individual tool calls.
2. **Poka-yoke v2 tool interface.** `check_hotel_ceiling(grade)` replaces both Exp 34's
   `check_rate_ceiling` and Exp 35C's `lookup_hotel_ceiling(city, country, year, grade)`. City and
   country are no longer model-supplied arguments at all — they are closed over from the claim's own
   `bill.city`/`bill.country` at tool-construction time, so a model that read the note's distractor city
   (X2-005's note says "Bengaluru", the bill says "Chennai") cannot pass the wrong one in even by
   mistake. The tool also returns the controlling clause ids (`TRV-2.2`, the year's `TRV-3.x`, `TRV-6.1`)
   directly, removing a second manual step.

## Result

| System | Correct/13 | FAR | HRR | Avg turns | Avg tool calls | Step-cap hits | Cost (13 cases) |
|---|---|---|---|---|---|---|---|
| Fixed workflow (Exp 18) | **7 (53.8%)** | 10.0% | 30.8% | — | 1/case | — | $0 |
| Old agent, pre-fetched RAG (Exp 20) | 7 (53.8%) | 30.0% | 23.1% | 5.69 | 1/turn | 3/13 | $0.043 |
| Agentic RAG v1 (Exp 34: sequential, raw-table interface) | 4 (30.8%) | 10.0% | 38.5% | 7.31 | 1/turn | 5/13 | $0.038 |
| **Agentic RAG v2 (Exp 36: parallel turns + poka-yoke v2)** | 4 (30.8%) | **0.0%** | 61.5% | 7.38 | **10.46 total (1.42/turn)** | **8/13** | $0.048 |

## X2-005, before and after

**Before (Exp 34, v1) — 7 calls, 8 turns, one call per turn, ends in a false approval:**
```
get_travel_request, get_exception_record, search_policy_corpus, check_rate_ceiling(ceiling=14500),
get_employee_profile, validate_approval, get_manager_approval
-> APPROVE  (WRONG: ceiling should be 9,800, IN-T2's fallback; 14,500 is IN-T1's, the wrong tier)
```

**After (Exp 36, v2) — 10 calls packed into 6 turns, genuine batching (e.g. employee profile + travel
request + project status + merchant metadata all issued together), and the ceiling is now correct:**
```
get_employee_profile + get_travel_request + get_project_status + get_merchant_metadata  (batched)
check_hotel_ceiling(grade='G4') -> {tier: IN-T2, ceiling: 9800.0, fallback_rule_applied: true}   <- FIXED
get_exception_record('EXC-0933') -> not found
validate_approval(required_level='M', required_types=['hotel'])   <- wrong enum, retried
validate_approval(required_level='MANAGER', required_types=['hotel'])   <- still wrong: 'hotel' is not
                                                                            a real approval_type (should
                                                                            be 'TRAVEL')
get_manager_approval, search_policy_corpus
-> REJECT  (still WRONG vs. expected REQUEST_INFORMATION -- but no longer a false approval)
```

## Reading the result honestly

**The targeted bug is fixed, cleanly and completely.** `check_hotel_ceiling` returned the correct 9,800
(IN-T2, fallback applied) for X2-005, and the same held across the batch for every hotel claim that
called it — the tier-substitution failure that caused Exp 34's false approval is gone. The poka-yoke
argument change (no model-supplied city) closed exactly the class of error it was built to close.

**But the case is still wrong, for a third, independent reason.** With the correct ceiling now in hand,
the model invented a bad argument for a different tool: it passed `required_types=['hotel']` to
`validate_approval` (lowercase, not a real approval type — `'TRAVEL'` is the correct value used
elsewhere in this exact trace), so the approval check itself came back confused, and REJECT was reached
by the wrong path. This is the third distinct, independently-confirmed bug this session has found on
this one case (tier substitution → fixed; REJECT-vs-REQUEST_INFORMATION disposition on a missing
exception → still open; now a validate_approval argument-type error → newly found). Fixing one layer's
failure mode reliably exposes the next one; it does not make the case correct end to end.

**Parallel turns did not solve the step-cap problem — it got worse, not better.** Average tool calls
per case rose to 10.46 (vs. Exp 34's turn-for-call ratio of 1:1), confirming genuine batching happened
(1.42 calls/turn). But average turns barely moved (7.38 vs. 7.31) and **step-cap hits rose from 5/13 to
8/13** — batching let the model pack more (including more wrong/retried) calls into the same turn
budget rather than finishing in fewer turns. `wrong_tool_calls` also rose, 29 vs. Exp 34's 15: more
calls per turn meant more opportunities per turn for a malformed argument (as above).

**The 0% FAR is real, but it is bought mostly by escalating more, not reasoning better.** Human review
rate rose to 61.5% (highest of any system tested this session) and every one of the 8 step-cap hits
resolved to the safe ESCALATE fallback; 3 of the 4 correct answers are ESCALATE-expected cases reached
this way. Only one case (X2-055, APPROVE) was a genuinely correct affirmative decision. Zero false
approvals is a legitimate safety win, but it should be read as "the system gave up and asked for human
review more often," not as "the system got better at judging when to approve."

## Decision
Accuracy is unchanged from Exp 34 (4/13) and still below both the fixed workflow and the old Exp 20
agent (7/13 each). The two upgrades delivered exactly what they were built for — the ceiling bug is
provably fixed, and false approvals dropped to zero — but neither upgrade raised overall correctness,
because each fix reliably reveals the next independent bug rather than resolving the case. The fixed
workflow remains the best-performing system on this 13-case set, and the selective resolver (Exp 30)
remains the project's frozen, final architecture; nothing in Exp 34, 35 or 36 has changed that
conclusion.
