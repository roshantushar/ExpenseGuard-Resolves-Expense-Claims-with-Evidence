"""Statistical helpers shared across evaluators: Wilson confidence intervals for small-sample rates
(FAR, accuracy) and percentile helpers for latency/cost distributions. No I/O, no ground-truth access."""
from __future__ import annotations
import math


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(math.ceil(q * len(xs))) - 1)] if xs else 0
