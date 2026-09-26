# Experiment 17 — Typed read-only enterprise tools

**Code:** `src/tools.py`, `tests/test_tools.py` · **Run tests:** `python -m unittest discover -s tests -v` (10 tests, all pass)

## Tools (8, all read-only)
`get_employee_profile`, `get_travel_request` (by employee and date), `get_manager_approval` (by expense id), `get_exception_record`, `get_project_status`, `search_previous_expenses` (optional merchant and date filters, capped at 10 rows), `get_conference_registration`, `get_merchant_metadata`. Descriptions say what each tool is for and, where confusion is likely, what it is not for (for example the exception tool is "not for ordinary manager approvals").

## Contract
Every call goes through `call_tool(name, args, timeout_s)` and returns `{"ok", "found", "data", "error"}`. It validates the tool name, the exact argument set, string types and identifier formats (`E0001`, `PRJ-001`, `EXC-WF-002`, `CONF-000`, `EXP-0084`, ISO dates), enforces a timeout, and never raises. A missing record is `ok: true, found: false, data: null`, distinct from an error. The tools read only the enterprise tables; a test asserts they never reference the ground-truth path and never emit label fields.

## Tests
Valid arguments for each tool; invalid identifiers; missing records; malformed arguments (missing, extra, non-string, empty, non-object); unknown tool; timeout; empty search result; response schema; read-only naming and description length; no ground-truth access.

## Bug found by the tests
The first run failed one test: an empty search result returned `data: []` instead of `null`. Fixed in `_res`. A file-handle leak in the table loader was fixed at the same time.

## Note
The "timeout" test simulates a slow tool; the real tools are in-memory lookups (well under a millisecond), so timeouts matter only once tools become real services.
