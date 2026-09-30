# Exp 19 — Agent-necessity audit ($0)

Notebook: `notebooks/exp19_agent_audit.ipynb`. Evaluator-side (reads private `branch_trigger`/`tool_path`; never used at runtime). $0.

**Question:** do any of the 13 group-C ("agent-candidate") dev claims genuinely need a model to decide what to look up next?

**Result: all 13 are conditional workflow-solvable; zero are genuinely agentic.** Inspecting each case's actual `tool_path` (not just the coarse `branch_trigger` text) shows every case reduces to one of three topologies — hotel-discovery, delegation-chain, project-budget-chain — and at every branch, the next tool is uniquely named by one field already in the prior result (an `event_id`, an approval `status`, a `parent_project_id`). No case requires choosing among several plausible tools or interpreting ambiguous evidence.

**Methodological note, disclosed:** a first pass used keyword-matching over the `branch_trigger` summary text and mis-classified 5/13 cases as "genuinely agentic" purely because their phrasing lacked expected keywords, even though the underlying check was an ordinary field comparison. Re-deriving the verdict from the actual `tool_path` corrected this. Lesson: audit the execution trace, not a natural-language summary of it.

**Exp 18 correctness (supporting evidence only, per instruction):** 7/13 conditional-workflow-solvable cases are already solved by the purely static `workflow_v2`; the 6 failures trace to documented implementation gaps (Exp 18), not to any case needing dynamic tool choice.

**Decision:** no case in the agent-candidate group requires a genuinely agentic architecture on this evidence. Per standing instruction, Exp 20's bounded-agent pilot still runs regardless, so the conclusion rests on measured pilot data too, not the audit alone.
