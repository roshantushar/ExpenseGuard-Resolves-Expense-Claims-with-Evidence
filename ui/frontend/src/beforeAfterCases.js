// Four real cases, one per decision outcome, each verified directly against the authoritative saved
// prediction files (not the precomputed UI export) before being used here. The APPROVE case is shown
// honestly as a case the frozen design gets WRONG — because a frozen-design APPROVE that is both
// correct AND resolved by the LLM-residual step does not exist anywhere in the 150-claim dataset (0/39
// APPROVE-truth cases go through the deterministic path successfully; the residual LLM never correctly
// predicts APPROVE). That is a real, documented finding (Exp 32/33), not a curation choice.
export const CASES = [
  {
    decision: "APPROVE",
    caseId: "X2-105",
    merchant: "Blossom & Co",
    amount: "JPY 5,400",
    note: "Gift for Ms. Wu at Ember Foods from Blossom & Co. Physical item, JPY.",
    reason: "All applicable checks pass — a compliant business gift under the annual/per-gift ceiling.",
    clauses: ["JP-3.1", "JP-3.2", "GIFT-2.1", "GIFT-2.2"],
    before: [
      "Reviewer manually opens the Japan regional addendum and the global gift policy — two separate documents",
      "Checks the per-gift ceiling AND the separate annual cumulative cap for this employee",
      "Confirms it's a physical item, not a cash-equivalent (different rules apply)",
      "Confirms the recipient's organization type doesn't trigger an anti-corruption restriction",
      "~15-20 minutes of manual cross-referencing before approving"
    ],
    after: [
      "Deterministic layer finds no conclusive rule — routes to the residual step",
      "Frozen design (official, shipped): single-shot LLM gets this WRONG — predicts REJECT",
      "Guarded-agent candidate: a dedicated check_gift_compliance tool computes the ceiling check in code — correctly APPROVES",
      "This is the system's most honest limitation, shown plainly: the official design's one weak component is exactly the APPROVE case"
    ],
    outcome: "guarded-correct-frozen-wrong"
  },
  {
    decision: "REJECT",
    caseId: "X2-060",
    merchant: "Keystone Supplies",
    amount: "SGD 1,899",
    note: "Bought workstation laptop at Keystone Supplies, SGD. Needed for my desk.",
    reason: "Capital asset — must be procured through Finance, not expensed.",
    clauses: ["SWE-2.1"],
    before: [
      "Reviewer must know the capital-asset threshold for equipment purchases",
      "Manually checks the claim amount against that threshold",
      "Manually explains to the employee why this can't be reimbursed and what the correct process is"
    ],
    after: [
      "Deterministic rule engine matches the equipment-threshold rule directly from the claim amount",
      "Resolved instantly, $0, no LLM call — the deterministic path is 100% accurate on unseen data",
      "Employee gets an evidence-cited reason (SWE-2.1) and the correct process, not just \"no\""
    ],
    outcome: "correct"
  },
  {
    decision: "REQUEST_INFORMATION",
    caseId: "X2-009",
    merchant: "OfficeMart",
    amount: "SGD 285",
    note: "Purchased project equipment from OfficeMart in Singapore. Adds to the kit for the lab related to the ongoing project.",
    reason: "Combined spend with a related recent purchase needs approval; none is on file.",
    clauses: ["DUP-2.1", "DUP-2.2", "APR-1.1"],
    before: [
      "This claim looks completely routine in isolation — nothing about it looks wrong",
      "Catching the issue requires a reviewer to manually search recent purchase history for the same employee/merchant/project",
      "Easy to miss by hand — the individual amount alone is well under any approval threshold"
    ],
    after: [
      "Split-transaction detection (Exp 14/15) automatically finds the related recent purchase and combines the amounts",
      "The combined total crosses the approval threshold — code computes this, not the model",
      "System asks for exactly the missing evidence (the combined-spend approval), not a vague \"more info needed\""
    ],
    outcome: "correct"
  },
  {
    decision: "ESCALATE",
    caseId: "X2-090",
    merchant: "DeskWorks",
    amount: "JPY 26,000",
    note: "Purchased project equipment for our lab from DeskWorks in Tokyo, Japan.",
    reason: "An approval of another type conflicts with this related spend.",
    clauses: ["DUP-2.1", "DUP-2.2", "JP-6.1", "APR-2.2"],
    before: [
      "The conflict is only visible by cross-referencing two separate approval records",
      "A reviewer only catches this if they happen to check — otherwise it's approved on the strength of one record alone",
      "No structured way to flag \"these two approvals disagree\" in a manual process"
    ],
    after: [
      "Deterministic checks resolve this conclusively — no LLM call needed",
      "The conflicting-approval-type check (added after Exp 28 found this exact gap) flags the disagreement directly",
      "Routed to a human reviewer with the specific conflict named, not a blanket \"needs review\""
    ],
    outcome: "correct"
  }
];
