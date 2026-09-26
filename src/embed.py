"""OpenRouter embeddings with disk cache, budget guard and logging. Stored indexes live in results/embeddings/."""
from __future__ import annotations
import hashlib, json, os, time
import numpy as np
from . import config as C, llm

C.load_env()
EMB_CACHE = C.RESULTS / "cache" / "emb"


def embed(model: str, texts: list, tag: str = "", run_id: str = "", batch: int = 64) -> np.ndarray:
    out = []
    for i in range(0, len(texts), batch):
        part = texts[i:i + batch]
        key = hashlib.sha256(json.dumps([model, part]).encode()).hexdigest()
        f = EMB_CACHE / f"{key}.json"
        if f.exists():
            r = json.loads(f.read_text()); cached = True
        else:
            cap = float(os.environ.get("MAX_BUDGET_USD") or 0)
            if not cap or llm.spent() >= cap:
                raise llm.BudgetExceeded("budget cap")
            t0 = time.time()
            j = llm._post("https://openrouter.ai/api/v1/embeddings", {"model": model, "input": part}, {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=180)
            u = j.get("usage", {})
            r = {"vectors": [d["embedding"] for d in sorted(j["data"], key=lambda d: d["index"])], "input_tokens": u.get("prompt_tokens", 0),
                 "cost_usd": u.get("cost", 0.0), "latency_ms": round((time.time() - t0) * 1000)}
            EMB_CACHE.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(r)); cached = False
        llm.log_event(type="llm_call", kind="embedding", run_id=run_id, experiment=tag, model=model, cached=cached, n_texts=len(part), cost_usd=r["cost_usd"],
                      input_tokens=r["input_tokens"], output_tokens=0, latency_ms=r["latency_ms"], cache_key=key[:12])
        out += r["vectors"]
    return np.array(out, dtype="float32")
