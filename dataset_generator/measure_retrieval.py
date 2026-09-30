"""Retrieval difficulty: identical retrievers, chunking and query builder over the V1 and V2 corpora. Reports Recall@K, Precision@K, MRR, nDCG and
all-required-clauses coverage, with and without the metadata filter. Evaluator-side (reads ground truth)."""
from __future__ import annotations
import json, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config as C, retrieval, embed, retrievers, retrieval_eval

EM = "voyageai/voyage-4-lite"; CFG = "recursive300_50"
SETS = {"V1": (ROOT / "ExpenseGuard_FINAL_CURRENT_DATASET", "required_policy_ids"), "V2": (ROOT / "ExpenseGuard_DATASET", "required_policy_ids")}


def jl(p): return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def run(name, D, key, k_list=(3, 5, 10)):
    C.POLICY = D / "01_policy_corpus"; retrieval.EMB = C.RESULTS / f"embeddings_measure_{name.lower()}"
    cases = jl(D / "02_cases" / "all_cases.jsonl"); gt = {g["case_id"]: g for g in jl(D / "04_ground_truth_PRIVATE" / "ground_truth.jsonl")}
    R = retrievers.Retriever(EM, CFG); qv = embed.embed(EM, [retrieval.claim_query(c) for c in cases], tag=f"MEASURE_{name}")
    out = {"n_chunks": len(R.chunks), "n_cases": len(cases), "avg_required_clauses": round(st.mean(len(gt[c["case_id"]][key]) for c in cases), 2)}
    for mode in ("bm25", "dense", "hybrid"):
        for filt in (False, True):
            for k in k_list:
                rows = []
                for c, q in zip(cases, qv):
                    req = set(gt[c["case_id"]][key])
                    hits = R.rank(mode, retrieval.claim_query(c), q, k, R.allowed(c) if filt else None)
                    rows.append(retrieval_eval.score(c, req, R.chunks, hits, k))
                out[f"{mode}|filter={filt}|k={k}"] = {m: round(st.mean(float(r[m]) for r in rows), 3) for m in ("recall", "precision", "rr", "ndcg", "full", "wrong_year_chunks", "wrong_region_chunks")}
    return out


if __name__ == "__main__":
    res = {n: run(n, *v) for n, v in SETS.items()}
    p = ROOT / "ExpenseGuard_DATASET" / "06_docs" / "retrieval_difficulty.json"
    p.write_text(json.dumps(res, indent=1))
    print(f"{'':6s}{'retriever':22s}{'K':>3s}  Recall  Prec   MRR   nDCG  all-required  wrong-year/case")
    for n in res:
        print(f"{n}: {res[n]['n_chunks']} chunks, {res[n]['n_cases']} cases, avg required clauses per case {res[n]['avg_required_clauses']}")
        for key, v in res[n].items():
            if isinstance(v, dict) and "filter=False" in key: print(f"   {key:26s} {v['recall']:.3f}  {v['precision']:.3f} {v['rr']:.3f} {v['ndcg']:.3f}   {v['full']:.3f}        {v['wrong_year_chunks']:.2f}")
        print("   with metadata filter:", {k.split('|')[0] + "@" + k.split('=')[-1]: (v['recall'], v['full']) for k, v in res[n].items() if isinstance(v, dict) and "filter=True" in k and "dense" in k})
