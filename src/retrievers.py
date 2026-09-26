"""Retrievers over one stored chunk index: BM25, dense (stored embeddings), hybrid (reciprocal rank fusion), optional metadata mask.
Runtime-safe: uses only the claim and chunk metadata (no ground truth)."""
from __future__ import annotations
import math, re
from collections import Counter
import numpy as np
from . import retrieval

REGION = {"Singapore": "SG", "India": "IN", "Japan": "JP"}


def _tok(t: str) -> list:
    return re.findall(r"\w+", t.lower())


class Retriever:
    def __init__(self, embed_model: str, cfg: str):
        self.idx = retrieval.build_or_load(embed_model, cfg)
        self.chunks = self.idx["chunks"]
        self.docs = [Counter(_tok(c["text"])) for c in self.chunks]
        self.len = np.array([sum(d.values()) for d in self.docs], dtype=float)
        self.df = Counter(w for d in self.docs for w in d)
        self.N = len(self.chunks)

    def bm25(self, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        s = np.zeros(self.N)
        avg = self.len.mean()
        for w in set(_tok(query)):
            if w not in self.df:
                continue
            idf = math.log(1 + (self.N - self.df[w] + 0.5) / (self.df[w] + 0.5))
            for i, d in enumerate(self.docs):
                f = d.get(w, 0)
                if f:
                    s[i] += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * self.len[i] / avg))
        return s

    def dense(self, qvec: np.ndarray) -> np.ndarray:
        return self.idx["vectors"].astype("float64") @ (qvec.astype("float64") / np.linalg.norm(qvec))

    def allowed(self, case: dict) -> np.ndarray:
        """Metadata filter from the claim only: document in force on the transaction date, and GLOBAL or the claim's own region."""
        d, r = case["transaction_date"], REGION.get(case["bill"]["country"], "")
        return np.array([c["effective_from"] <= d <= c["effective_to"] and c["region"] in ("GLOBAL", r) for c in self.chunks])

    def rank(self, mode: str, query: str, qvec: np.ndarray, k: int, mask: np.ndarray = None) -> list:
        """Returns [(chunk_index, score)] for the top k. mode: bm25 | dense | hybrid (RRF, k=60)."""
        if mode == "bm25":
            s = self.bm25(query)
        elif mode == "dense":
            s = self.dense(qvec)
        else:
            rr = np.zeros(self.N)
            for sc in (self.bm25(query), self.dense(qvec)):
                order = np.argsort(-sc)
                for rank, i in enumerate(order):
                    rr[i] += 1 / (60 + rank + 1)
            s = rr
        if mask is not None:
            s = np.where(mask, s, -np.inf)
        order = [int(i) for i in np.argsort(-s) if np.isfinite(s[i])][:k]
        return [(i, float(s[i])) for i in order]

    def context(self, hits: list) -> str:
        return "\n\n".join(f"[{self.chunks[i]['doc_id']} | region {self.chunks[i]['region']} | effective {self.chunks[i]['effective_from']} to {self.chunks[i]['effective_to']}]\n{self.chunks[i]['text']}" for i, _ in hits)
