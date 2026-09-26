"""Dense retrieval over stored chunk embeddings. Indexes are saved once and re-used by later experiments."""
from __future__ import annotations
import json
import numpy as np
from . import config as C, chunking, embed

EMB = C.RESULTS / "embeddings"


def _dir(model: str, cfg: str):
    return EMB / model.replace("/", "_").replace(":", "_") / cfg


def build_or_load(model: str, cfg: str) -> dict:
    d = _dir(model, cfg)
    if (d / "vectors.npy").exists():
        return {"chunks": [json.loads(l) for l in (d / "chunks.jsonl").read_text().splitlines()], "vectors": np.load(d / "vectors.npy"), "model": model, "cfg": cfg}
    chunks = chunking.chunk(cfg)
    v = embed.embed(model, [c["text"] for c in chunks], tag="INDEX_BUILD")
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "chunks.jsonl").write_text("\n".join(json.dumps(c) for c in chunks) + "\n")
    np.save(d / "vectors.npy", v)
    return {"chunks": chunks, "vectors": v, "model": model, "cfg": cfg}


def claim_query(c: dict) -> str:
    """Raw claim-derived query: no rewriting, no ground truth."""
    b = c["bill"]
    return f"{b['merchant_category']} {b['country']} {c['transaction_date']} " + "; ".join(i["description"] for i in b["line_items"]) + ". " + c["employee_description"]


def search(idx: dict, qvec: np.ndarray, k: int) -> list:
    q = qvec.astype("float64") / np.linalg.norm(qvec)
    s = idx["vectors"].astype("float64") @ q  # float64 avoids spurious Accelerate BLAS warnings on macOS
    return [(int(i), float(s[i])) for i in np.argsort(-s)[:k]]
