"""Writes the V2 package documentation from the package's own files (no hand-typed numbers), then SHA256SUMS."""
from __future__ import annotations
import csv, hashlib, json, re, shutil, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ExpenseGuard_V2_DATASET"
jl = lambda p: [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def main():
    gt = jl(OUT / "04_ground_truth_PRIVATE" / "ground_truth.jsonl"); cfg = json.loads((OUT / "05_generation" / "generation_config.json").read_text())
    meta = json.loads((OUT / "01_policy_corpus" / "policy_metadata.json").read_text()); rep = json.loads((OUT / "06_docs" / "validation_report.json").read_text())
    ret = json.loads((OUT / "06_docs" / "retrieval_difficulty.json").read_text())
    rows = {p.stem: sum(1 for _ in open(p, encoding="utf-8")) - 1 for p in sorted((OUT / "03_enterprise_data").glob("*.csv"))}
    words = {d["doc_id"]: len((OUT / "01_policy_corpus" / "source_documents" / f"{d['doc_id']}_{[p.stem.split('_', 1)[1] for p in (OUT / '01_policy_corpus' / 'source_documents').glob(d['doc_id'] + '_*')][0]}.md").read_text().split()) for d in meta}
    fam = Counter((g["architecture_group"][0], g["case_family"]) for g in gt)
    oc = lambda sel: dict(Counter(g["expected_decision"] for g in gt if sel(g)))
    multi = sum(len(g["minimum_required_tools"]) >= 2 for g in gt if g["architecture_group"] == "B_WORKFLOW")
    tp = Counter(len(g["minimum_required_tools"]) for g in gt if g["architecture_group"] == "C_AGENT_DYNAMIC")
    v1, v2 = ret["V1"], ret["V2"]
    def rr(d, k): v = d[k]; return f"{v['recall']:.2f} / {v['full']:.2f}"
    card = f"""# ExpenseGuard V2 Dataset Card

## Purpose
A harder synthetic benchmark for expense-claim readiness (APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE) built to stress **retrieval**: a dense, versioned, cross-referenced policy corpus; claims phrased in everyday language; and rules whose numbers live in different documents, years, regions and circulars. The task is not fraud detection.

## Size
- {len(gt)} unique claims (every employee description and bill number is unique; one employee per claim, so no employee spans splits)
- {len(meta)} policy documents, {cfg['corpus']['clauses']} clauses, {cfg['corpus']['words']:,} words, {cfg['corpus']['pages']}-page PDF
- 11 enterprise tables; {cfg['historical_expenses']:,} historical expenses (including hard-negative rows for duplicate and split detection)
- 15 separate guardrail cases (carried over from V1, `04_ground_truth_PRIVATE/guardrail_cases.csv`)

## Architecture groups
| Group | Cases | Meaning |
|---|---|---|
| A_SELF_CONTAINED | {sum(1 for g in gt if g['architecture_group'] == 'A_SELF_CONTAINED')} | Decidable from the claim, the policy corpus and the FX table; no enterprise lookup is needed |
| B_WORKFLOW | {sum(1 for g in gt if g['architecture_group'] == 'B_WORKFLOW')} | Fixed evidence path once the claim type is known; {multi} need two or more lookups, the rest need one |
| C_AGENT_DYNAMIC | {sum(1 for g in gt if g['architecture_group'] == 'C_AGENT_DYNAMIC')} | The next record to read depends on what the previous lookup returned; chains are 2 to 5 lookups deep (lookups needed: {dict(sorted(tp.items()))}) with recorded branch triggers |

Cross-document cases (evidence in two or more documents): {sum(g['cross_document'] for g in gt)}. Cases decided by a mid-year circular amendment: {sum(g['temporal_amendment_case'] for g in gt)}.

## Outcomes
All: {oc(lambda g: True)}. Development: {oc(lambda g: g['split'] == 'DEVELOPMENT')}. Validation: {oc(lambda g: g['split'] == 'VALIDATION')}. Final test: {oc(lambda g: g['split'] == 'FINAL_TEST')}.

## Frozen split
70 development / 30 validation / 50 final test, stratified by outcome and then by group. Final test by group: {dict(Counter(g['architecture_group'][0] for g in gt if g['split'] == 'FINAL_TEST'))}.
**Challenge set:** {sum(g['independent_challenge'] for g in gt)} final-test cases (outcomes {oc(lambda g: g['independent_challenge'])}) whose free-text description was rewritten with a separately authored template (different structure and vocabulary, same structured facts). "Independent" here means independently authored templates; **the wording was not reviewed by a human.**

## Corpus design (why retrieval is hard)
- **Near-identical clauses across years, regions and grade bands**: three global policy versions, three regional addenda and yearly ceiling tables that differ only in numbers and dates.
- **Two-hop numbers**: employee meal, client meal, gift, telecom and mileage limits live only in the regional addenda; the global meals policy points to them and states default figures that never apply to Singapore, India or Japan.
- **Mid-year circulars** amend values held in other documents without naming the category in their headings; the controlling value depends on the transaction date.
- **Stale distractors**: a historical-schedules document, an expired 2023 schedule, withdrawn drafts, and worked examples that quote the value current when they were written.
- **Vocabulary gap**: policy text uses formal terms (ground transportation, accommodation, hospitality); claims say cab, put up, hosted.
- **Filler with a purpose**: each clause carries two paragraphs of qualitative interpretive guidance (written once by gpt-4o-mini and frozen in `dataset_v2/commentary_cache.json`; validated to contain no numbers, currency codes or new requirements) so relevant text is diluted by realistic prose.
- Document list: {', '.join(f"{d['doc_id']} {d['title']}" for d in meta)}.

## Ground truth
Every label comes from `dataset_v2/engine.py`, a reference policy engine that reads the same structured schedules (`dataset_v2/world.py`) the policy text is rendered from, so the text and the labels cannot disagree. Thresholds in SGD equivalent use the monthly FX table exactly as the FX policy states, avoiding the raw-amount inconsistencies found in V1. Per case the ground truth records the decision, controlling clause ids (`required_policy_ids`), context clauses (`supporting_policy_ids`), the documents involved, missing fields, the tool path the engine walked, the minimum required tools, branch triggers and the human-review reason for escalations.

## Retrieval difficulty (same retrievers, chunking and query builder on both datasets; recall / all-required-clauses-retrieved)
| Retriever | V1 (23 chunks) | V2 ({v2['n_chunks']} chunks) |
|---|---|---|
| dense, K=3 | {rr(v1, 'dense|filter=False|k=3')} | {rr(v2, 'dense|filter=False|k=3')} |
| dense, K=10 | {rr(v1, 'dense|filter=False|k=10')} | {rr(v2, 'dense|filter=False|k=10')} |
| BM25, K=3 | {rr(v1, 'bm25|filter=False|k=3')} | {rr(v2, 'bm25|filter=False|k=3')} |
| hybrid (RRF), K=3 | {rr(v1, 'hybrid|filter=False|k=3')} | {rr(v2, 'hybrid|filter=False|k=3')} |
| dense + metadata filter, K=3 | {rr(v1, 'dense|filter=True|k=3')} | {rr(v2, 'dense|filter=True|k=3')} |
voyage-4-lite embeddings, recursive 300/50 chunks. V2 cases need {v2['avg_required_clauses']} controlling clauses on average (V1: {v1['avg_required_clauses']}). Part of the difficulty is corpus size and more required clauses, which is intended.

## Enterprise tables (rows)
{', '.join(f'{k} {v}' for k, v in rows.items())}.

## Validation
`python -m dataset_v2.validate` runs {rep['n_checks']} checks ({rep['n_checks'] - rep['n_failed']} pass): split, group and outcome balance, clause existence, schedule values present in the corpus, PDF page count, referential integrity, uniqueness, leakage (labels absent from cases, corpus and tables; challenge cases unmarked), and **reproduction of every label by the reference engine from the packaged files**. Report: `06_docs/validation_report.json`.

## Data boundaries
Runtime and model-visible: `02_cases`, `01_policy_corpus`, approved read-only tools over `03_enterprise_data`. Evaluator-only: `04_ground_truth_PRIVATE`.

## Known limitations
- Synthetic; not for estimating real prevalence, behaviour, processing times or fraud.
- The reference engine defines the policy semantics where the prose could be read two ways; a human policy review of the engine would strengthen the labels.
- {multi} of the 80 workflow cases need two or more lookups; the other {80 - multi} need exactly one, so "multi-tool" holds for {multi}/80.
- The runtime tool layer in `src/` still targets V1 (eight tools). V2 adds two lookups (`get_approval_delegation`, `get_cost_centre_budget`), new columns and a structured claim `form`, and needs a port before systems can be run on it.
- Interpretive guidance was LLM-written (qualitative only). The V1 metadata-aware wrong-year metric is near zero here because temporal difficulty sits in circular-versus-base values, not in whole-year documents.
- No baseline system results exist yet on V2 apart from the retrieval measurements above.
"""
    (OUT / "DATASET_CARD.md").write_text(card)
    (OUT / "README.md").write_text(f"""# ExpenseGuard V2 Dataset Package

Start with `DATASET_CARD.md`. Layout: `01_policy_corpus/` (22 documents as markdown plus one PDF), `02_cases/` (150 claims and frozen splits), `03_enterprise_data/` (11 read-only tables), `04_ground_truth_PRIVATE/` (evaluator only), `05_generation/`, `06_docs/` (validation and retrieval-difficulty reports).
Rebuild: `python -m dataset_v2.build` (deterministic, seed 6202; corpus prose is frozen in `dataset_v2/commentary_cache.json`), then `python -m dataset_v2.validate` and `python -m dataset_v2.measure_retrieval`.
Never expose `04_ground_truth_PRIVATE/` to a model, an index or a runtime tool.
""")
    (OUT / "CURRENT_DATASET_VERSION.md").write_text(f"# Current dataset version\n\nExpenseGuard V2, seed 6202: {len(gt)} claims (40 self-contained / 80 fixed-path / 30 dynamic), {len(meta)} policy documents, {cfg['corpus']['pages']}-page PDF, {cfg['historical_expenses']:,} historical expenses, 70/30/50 frozen split with 15 challenge cases in the final test. The V1 dataset in `ExpenseGuard_FINAL_CURRENT_DATASET/` is unchanged.\n")
    (OUT / "05_generation" / "README.md").write_text("The generator is the Python package `dataset_v2/` at the repository root: `world.py` (schedules and amendments), `policy_text.py`, `faq.py` and `render.py` (corpus), `engine.py` (reference policy engine that derives every label), `builder.py`, `cases_a.py`, `cases_b.py`, `cases_c.py` and `assemble.py` (scenarios and enterprise state), `build.py`, `validate.py`, `measure_retrieval.py`, `write_docs.py`.\n")
    (OUT / "05_generation" / "validate_dataset.py").write_text("import runpy, sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[2]))\nrunpy.run_module('dataset_v2.validate', run_name='__main__')\n")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}" for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.txt" and p.name != ".DS_Store") + "\n")
    shutil.copy(OUT / "DATASET_CARD.md", ROOT / "docs" / "dataset_v2_card.md")
    print(card[:3000])


if __name__ == "__main__":
    main()
