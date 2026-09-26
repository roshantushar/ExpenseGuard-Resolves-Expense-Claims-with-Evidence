"""ExpenseGuard V2 - corpus rendering: interpretive commentary (LLM, qualitative only, cached and frozen), markdown sources, HTML, PDF (headless Chrome), metadata."""
from __future__ import annotations
import html, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from . import policy_text, faq

CACHE = Path(__file__).resolve().parent / "commentary_cache.json"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SYSTEM = ("You write interpretive guidance for an internal corporate expense policy manual of a fictional company. For each clause you receive (id, title, normative text) write TWO paragraphs of about 90 to 120 words each. "
          "Paragraph A: the purpose of the clause and the typical business situations it covers. Paragraph B: common misunderstandings and how the topic relates conceptually to neighbouring policy topics. "
          "STRICT RULES: use a formal policy register; do not state, restate or hint at any number, amount, percentage, date, threshold, limit, currency code or grade label; do not add any new requirement, limit, approval, exception or "
          "procedure that is not already in the clause; do not contradict the clause; do not repeat the clause title more than once. Return ONLY JSON: {\"notes\": [{\"id\": \"...\", \"a\": \"...\", \"b\": \"...\"}]}.")
BAD = re.compile(r"\d|%|\b(SGD|INR|JPY|percent)\b", re.I)


def _valid(t):
    w = len(t.split())
    return isinstance(t, str) and 60 <= w <= 170 and not BAD.search(re.sub(r"Tier-\d", "Tier", t))


def commentary(all_docs, model="openai/gpt-4o-mini"):
    from src import llm
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [c for d in all_docs if d["key"] not in ("HIST", "FAQ") for c in d["clauses"] if c["id"] not in cache]
    for i in range(0, len(todo), 6):
        batch = todo[i:i + 6]
        for attempt in range(3):
            user = "Clauses:\n" + "\n\n".join(f"[{c['id']}] {c['title']}: {re.sub(chr(10) + '+', ' ', c['text'])[:900]}" for c in batch)
            if attempt: user += "\n\nReminder: NO digits, NO percent signs, NO currency codes, NO thresholds in your paragraphs."
            r = llm.chat(model, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], temperature=0.4 + 0.1 * attempt, max_tokens=2600, tag="V2_CORPUS")
            try:
                notes = {n["id"]: n for n in json.loads(r["text"])["notes"]}
            except Exception:
                continue
            for c in batch:
                n = notes.get(c["id"])
                if n and _valid(n.get("a", "")) and _valid(n.get("b", "")) and c["id"] not in cache:
                    cache[c["id"]] = {"a": n["a"].strip(), "b": n["b"].strip()}
            batch = [c for c in batch if c["id"] not in cache]
            if not batch:
                break
        CACHE.write_text(json.dumps(cache, indent=1))
    return cache


def md_table_to_html(text):
    out, buf = [], []
    def flush():
        if buf:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in buf if not re.fullmatch(r"\|[-| ]+\|", r.strip())]
            out.append("<table>" + "".join(("<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{html.escape(c)}</{'th' if i == 0 else 'td'}>" for c in r) + "</tr>") for i, r in enumerate(rows)) + "</table>")
            buf.clear()
    for line in text.split("\n"):
        if line.startswith("|"):
            buf.append(line)
        else:
            flush()
            if line.strip():
                out.append(f"<p>{html.escape(line)}</p>")
    flush()
    return "\n".join(out)


def build_corpus(out: Path, font_pt=None):
    all_docs = policy_text.docs() + [faq.d22()]
    notes = commentary(all_docs)
    src = out / "source_documents"; src.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.md"): f.unlink()
    meta, words, htmls = [], 0, []
    for d in all_docs:
        lines = [f"# {d['title']}", "", f"Document ID: {d['id']}", f"Region: {d['region']}", f"Effective: {d['eff'][0]} to {d['eff'][1]}", f"Category: {d['category']}", "",
                 f"> Internal policy document of {policy_text.CO}. Precedence rank {d['rank']} (lower rank overrides higher rank where documents differ).", ""]
        hl = [f"<h1>{html.escape(d['title'])}</h1><p class='meta'>Document ID {d['id']} · Region {d['region']} · Effective {d['eff'][0]} to {d['eff'][1]} · Category {d['category']}</p>"]
        for c in d["clauses"]:
            lines += [f"## {c['id']} - {c['title']}", "", c["text"], ""]
            hl.append(f"<h2>{c['id']} - {html.escape(c['title'])}</h2>" + md_table_to_html(c["text"]))
            n = notes.get(c["id"])
            if n:
                lines += [f"Interpretive guidance: {n['a']}", "", n["b"], ""]
                hl.append(f"<p class='note'><b>Interpretive guidance.</b> {html.escape(n['a'])}</p><p class='note'>{html.escape(n['b'])}</p>")
        text = "\n".join(lines)
        words += len(text.split())
        (src / f"{d['id']}_{d['key']}.md").write_text(text, encoding="utf-8")
        meta.append(dict(doc_id=d["id"], title=d["title"], region=d["region"], effective_from=d["eff"][0], effective_to=d["eff"][1], category=d["category"], precedence_rank=d["rank"],
                         clause_ids=[c["id"] for c in d["clauses"]]))
        htmls.append("<section>" + "\n".join(hl) + "</section>")
    (out / "policy_metadata.json").write_text(json.dumps(meta, indent=1))
    css = lambda pt: f"@page{{size:A4;margin:14mm 13mm}}body{{font-family:Georgia,serif;font-size:{pt}pt;line-height:1.28;color:#111}}h1{{font-size:{pt + 5}pt;margin:0 0 4pt;page-break-before:always}}section:first-child h1{{page-break-before:avoid}}h2{{font-size:{pt + 1}pt;margin:8pt 0 2pt}}p{{margin:2pt 0;text-align:justify}}p.meta{{color:#555;font-size:{pt - 1}pt}}p.note{{color:#222}}table{{border-collapse:collapse;margin:3pt 0;font-size:{pt - 1}pt}}td,th{{border:0.5pt solid #999;padding:1pt 4pt}}"
    pdf = out / "Northstar_Expense_Policy_Corpus_2024_2026.pdf"
    import pypdf
    pages = 0
    for pt in ([font_pt] if font_pt else [11, 10.5, 10, 9.5, 9, 8.5, 8]):
        (out / "_corpus.html").write_text(f"<html><head><meta charset='utf-8'><style>{css(pt)}</style></head><body>{''.join(htmls)}</body></html>", encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"file://{out / '_corpus.html'}"], capture_output=True, timeout=180)
        pages = len(pypdf.PdfReader(str(pdf)).pages)
        if pages <= 74:
            break
    (out / "_corpus.html").unlink()
    return dict(docs=len(all_docs), clauses=sum(len(d["clauses"]) for d in all_docs), words=words, pages=pages, font_pt=pt, commentary_clauses=len(notes))
