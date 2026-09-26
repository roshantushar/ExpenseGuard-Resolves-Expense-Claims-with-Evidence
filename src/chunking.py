"""Chunking of the policy corpus (12 source documents, verbatim). Every chunk carries document metadata and
the ids of the clauses it covers (used only by the evaluator for Recall/Precision; never shown to a model).
Token counts are approximated as words / 0.75 (no tokenizer dependency)."""
from __future__ import annotations
import re
from . import config as C

WORDS_PER_TOKEN = 0.75


def documents() -> list:
    docs = []
    for p in sorted((C.POLICY / "source_documents").glob("*.md")):
        t = p.read_text(encoding="utf-8")
        eff = re.search(r"Effective: (\S+) to (\S+)", t)
        docs.append({"doc_id": re.search(r"Document ID: (\S+)", t).group(1), "region": re.search(r"Region: (\S+)", t).group(1),
                     "effective_from": eff.group(1), "effective_to": eff.group(2), "category": re.search(r"Category: (\S+)", t).group(1), "text": t})
    return docs


def _clause_spans(text: str) -> list:
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^## (\S+) - ", text, re.M)]
    return [(cid, s, heads[i + 1][0] if i + 1 < len(heads) else len(text)) for i, (s, cid) in enumerate(heads)]


def _covered(text: str, s: int, e: int) -> list:
    """Clauses whose text overlaps the span [s, e) by at least half of the clause length."""
    return [cid for cid, a, b in _clause_spans(text) if max(0, min(e, b) - max(s, a)) >= 0.5 * (b - a)]


SEPS = ["\n## ", "\n\n", "\n", ". ", " "]  # recursive separators, coarse to fine: clause heading, paragraph, line, sentence, word


def _nw(t: str, s: int, e: int) -> int:
    return len(t[s:e].split())


def _atoms(t: str, s: int, e: int, size: int, seps: list) -> list:
    """Recursively split t[s:e] on the coarsest separator present until every piece has <= size words."""
    if _nw(t, s, e) <= size or not seps:
        return [(s, e)]
    sep, rest = seps[0], seps[1:]
    skip = 1 if sep == "\n## " else len(sep)  # cut before the '##' heading, otherwise after the separator
    cuts = sorted({s, e} | {s + m.start() + skip for m in re.finditer(re.escape(sep), t[s:e])})
    if len(cuts) <= 2:
        return _atoms(t, s, e, size, rest)
    out = []
    for a, b in zip(cuts, cuts[1:]):
        out += _atoms(t, a, b, size, rest) if _nw(t, a, b) > size else [(a, b)]
    return out


def _recursive(t: str, size: int, ov: int) -> list:
    atoms = _atoms(t, 0, len(t), size, SEPS)
    spans, i = [], 0
    while i < len(atoms):
        j, w = i, 0
        while j < len(atoms) and (w + _nw(t, *atoms[j]) <= size or j == i):
            w += _nw(t, *atoms[j]); j += 1
        spans.append((atoms[i][0], atoms[j - 1][1]))
        if j >= len(atoms):
            break
        k, back = j, 0  # overlap: step back over trailing atoms totalling <= ov words
        while k - 1 > i and back + _nw(t, *atoms[k - 1]) <= ov:
            back += _nw(t, *atoms[k - 1]); k -= 1
        i = k
    return spans


def chunk(cfg: str) -> list:
    """cfg: 'fixed{tokens}_{overlap}' e.g. fixed300_50, or 'clause' (one chunk per clause, structure-aware)."""
    out = []
    for d in documents():
        t = d["text"]
        meta = {k: d[k] for k in ("doc_id", "region", "effective_from", "effective_to", "category")}
        if cfg == "clause":
            spans = [(cid, a, b) for cid, a, b in _clause_spans(t)]
            for i, (cid, a, b) in enumerate(spans):
                out.append({"chunk_id": f"{d['doc_id']}#{cid}", **meta, "text": f"[{d['doc_id']} | region {d['region']} | effective {d['effective_from']} to {d['effective_to']}]\n" + t[a:b].strip(),
                            "clause_ids": [cid]})
            continue
        if cfg.startswith("recursive"):
            size, ov = (int(int(x) * WORDS_PER_TOKEN) for x in re.fullmatch(r"recursive(\d+)_(\d+)", cfg).groups())
            for n, (a, b) in enumerate(_recursive(t, size, ov)):
                out.append({"chunk_id": f"{d['doc_id']}~{n}", **meta, "text": t[a:b].strip(), "clause_ids": _covered(t, a, b)})
            continue
        size, ov = (int(x) for x in re.fullmatch(r"fixed(\d+)_(\d+)", cfg).groups())
        size, ov = int(size * WORDS_PER_TOKEN), int(ov * WORDS_PER_TOKEN)
        words = [(m.start(), m.end()) for m in re.finditer(r"\S+", t)]
        i = n = 0
        while i < len(words):
            j = min(i + size, len(words))
            s, e = words[i][0], words[j - 1][1]
            out.append({"chunk_id": f"{d['doc_id']}@{n}", **meta, "text": t[s:e], "clause_ids": _covered(t, s, e)})
            if j == len(words):
                break
            i += size - ov; n += 1
    return out
