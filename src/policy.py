"""Policy corpus loader: clause id -> text with document header (region, effective dates)."""
from __future__ import annotations
import re
from functools import lru_cache
from . import config as C


@lru_cache(maxsize=1)
def clauses() -> dict:
    out = {}
    for p in sorted((C.POLICY / "source_documents").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        doc = re.search(r"Document ID: (\S+)", txt).group(1)
        region = re.search(r"Region: (\S+)", txt).group(1)
        eff = re.search(r"Effective: (.+)", txt).group(1).strip()
        for m in re.finditer(r"^## (\S+) - (.+?)\n\n(.*?)(?=\n## |\Z)", txt, re.S | re.M):
            body = m.group(3).split("\n\nOperational note")[0].strip()
            out[m.group(1)] = {"id": m.group(1), "doc": doc, "region": region, "effective": eff, "title": m.group(2), "text": body}
    return out


def render(ids) -> str:
    cl = clauses()
    return "\n\n".join(f"[{i}] ({cl[i]['doc']}, region {cl[i]['region']}, effective {cl[i]['effective']}) {cl[i]['title']}: {cl[i]['text']}" for i in ids)
