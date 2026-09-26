"""LLM client: OpenRouter (paid) and Ollama (local/free). Disk cache, spend ledger, hard budget cap.
Uses only the standard library."""
from __future__ import annotations
import hashlib, json, os, time, urllib.request
from . import config as C

C.load_env()
CACHE = C.RESULTS / "cache"
LEDGER = C.RESULTS / "run_log.jsonl"  # single log of everything: llm calls, per-case results, experiment summaries
# USD per 1M tokens, fallback only if the API does not report cost
PRICES = {"openai/gpt-4o-mini": (0.15, 0.60)}


class BudgetExceeded(RuntimeError):
    pass


def log_event(**row) -> None:
    """Append one row to the single run log. `type` is llm_call | case_result | experiment_summary."""
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **row}, default=str) + "\n")


def spent() -> float:
    """Real OpenRouter spend: fresh (non-cached) calls only."""
    if not LEDGER.exists():
        return 0.0
    rows = (json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip())
    return sum(r["cost_usd"] for r in rows if r.get("type") == "llm_call" and not r.get("cached"))


def _post(url, payload, headers, timeout=120):
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def chat(model: str, messages: list, temperature: float = 0.0, max_tokens: int = 600, tag: str = "", case_id: str = "", run_id: str = "", split: str = "") -> dict:
    """Returns {text, input_tokens, output_tokens, cost_usd, latency_ms, cached, model}."""
    key = hashlib.sha256(json.dumps([model, messages, temperature, max_tokens], sort_keys=True).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        out = json.loads(f.read_text())
        log_event(type="llm_call", run_id=run_id, split=split, experiment=tag, case_id=case_id, model=model, cached=True, cost_usd=out["cost_usd"],
                  input_tokens=out["input_tokens"], output_tokens=out["output_tokens"], latency_ms=out["latency_ms"], cache_key=key[:12])
        return {**out, "cached": True}
    local = "/" not in model  # ollama tags have no provider prefix
    if not local:
        cap = float(os.environ.get("MAX_BUDGET_USD") or 0)
        if not cap or spent() >= cap:
            raise BudgetExceeded(f"spent ${spent():.4f} >= cap ${cap}")
    t0 = time.time()
    if local:
        r = _post("http://localhost:11434/api/chat", {"model": model, "messages": messages, "stream": False, "format": "json",
                  "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": 16384}}, {}, timeout=600)
        out = {"text": r["message"]["content"], "input_tokens": r.get("prompt_eval_count", 0), "output_tokens": r.get("eval_count", 0), "cost_usd": 0.0}
    else:
        r = _post("https://openrouter.ai/api/v1/chat/completions",
                  {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
                   "response_format": {"type": "json_object"}, "usage": {"include": True}},
                  {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
        u = r["usage"]
        pin, pout = PRICES.get(model, (0, 0))
        cost = u.get("cost", (u["prompt_tokens"] * pin + u["completion_tokens"] * pout) / 1e6)
        out = {"text": r["choices"][0]["message"]["content"], "input_tokens": u["prompt_tokens"], "output_tokens": u["completion_tokens"], "cost_usd": cost}
    out.update(latency_ms=round((time.time() - t0) * 1000), model=model)
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out))
    log_event(type="llm_call", run_id=run_id, split=split, experiment=tag, case_id=case_id, model=model, cached=False, cost_usd=out["cost_usd"],
              input_tokens=out["input_tokens"], output_tokens=out["output_tokens"], latency_ms=out["latency_ms"], cache_key=key[:12])
    return {**out, "cached": False}
