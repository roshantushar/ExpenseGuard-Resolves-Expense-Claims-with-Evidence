"""Minimal local backend for the ExpenseGuard demo UI's "run live" mode. Stdlib only (no new
dependency) -- runs the ACTUAL Python resolver/agent code on request, so a live run is never a
re-implementation, just the real system called on demand instead of read from the precomputed export.

Usage: python -m ui.backend.server            (serves on http://localhost:8787)

Endpoints:
  GET  /api/cases                              -> the same cases.json the frontend also has bundled
  POST /api/run  {case_id, design, model}       -> runs that one case live and returns decision + trace
       design: "frozen" | "agent"
       model: any OpenRouter model id (default: PAID_MODEL from .env); the caller's own choice, so a
       live run against a paid model is always an explicit, visible choice -- never triggered silently.

This is intentionally single-purpose and unauthenticated: for local demo use only, not for deployment
as-is (no rate limiting, no auth, and it spends real money against MAX_BUDGET_USD when "design":"agent"
or a paid model is chosen).
"""
from __future__ import annotations
import json, os, sys, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src import config as C, llm_exp, resolver, agent as A, agent_variants as V  # noqa: E402

C.load_env()
_ALL_CASES = {c["case_id"]: c for split in ("DEVELOPMENT", "VALIDATION", "FINAL_TEST") for c in llm_exp.cases_for(split)}
CASES_JSON = ROOT / "ui" / "frontend" / "public" / "data" / "cases.json"


def _clean_trace(trace):
    out = []
    for step in trace or []:
        obs = step.get("observation", {}) or {}
        out.append({"tool": step["tool"], "args": step.get("args", {}), "ok": obs.get("ok"), "found": obs.get("found"), "data": obs.get("data"), "error": obs.get("error")})
    return out


def run_live(case_id: str, design: str, model: str | None) -> dict:
    case = _ALL_CASES.get(case_id)
    if not case:
        return {"error": f"unknown case_id: {case_id}"}
    if design == "frozen":
        d, conclusive = resolver.deterministic(case)
        if conclusive:
            return {"decision": d["decision"], "path": "deterministic", "policy_evidence": d.get("policy_evidence", []),
                    "missing_fields": d.get("missing_fields", []), "explanation": d.get("reason"), "trace": []}
        out = resolver.resolve_batch([case], model=model)
        r = out[case_id]
        return {"decision": r["decision"], "path": "llm_residual", "policy_evidence": r.get("policy_evidence", []),
                "missing_fields": r.get("missing_fields", []), "explanation": r.get("explanation"), "trace": []}
    if design == "agent":
        specs, case_tools = V.specs_and_tools_47(case)
        r = A.run(case, model=model, system_template=V.SYSTEM_47, specs=specs, case_tools=case_tools, max_steps=8)
        r = V.gate_disposition(V.gate_approve(r))
        return {"decision": r["decision"], "policy_evidence": r.get("policy_evidence", []), "missing_fields": r.get("missing_fields", []),
                "explanation": r.get("explanation"), "turns": r.get("turns"), "cost_usd": r.get("cost_usd"), "trace": _clean_trace(r.get("trace"))}
    return {"error": f"unknown design: {design!r}, expected 'frozen' or 'agent'"}


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path == "/api/cases":
            self.send_response(200); self.send_header("Content-Type", "application/json"); self._cors(); self.end_headers()
            self.wfile.write(CASES_JSON.read_bytes())
            return
        self.send_response(404); self._cors(); self.end_headers()

    def do_POST(self):
        if self.path != "/api/run":
            self.send_response(404); self._cors(); self.end_headers(); return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            result = run_live(body.get("case_id"), body.get("design", "agent"), body.get("model") or None)
            code = 200
        except Exception as e:  # noqa
            result = {"error": f"{type(e).__name__}: {e}", "trace_text": traceback.format_exc(limit=3)}
            code = 500
        self.send_response(code); self.send_header("Content-Type", "application/json"); self._cors(); self.end_headers()
        self.wfile.write(json.dumps(result, default=str).encode())

    def log_message(self, fmt, *args):
        print(f"[ui-backend] {self.address_string()} {fmt % args}")


def main():
    port = int(os.environ.get("UI_BACKEND_PORT", 8787))
    print(f"ExpenseGuard demo backend on http://localhost:{port} ({len(_ALL_CASES)} cases loaded)")
    ThreadingHTTPServer(("localhost", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
