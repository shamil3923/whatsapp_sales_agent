"""
Statistics for the eval harness: bootstrap intervals and paired significance.

Why these two specifically:

  A bootstrap CI, because the per-category slices are 15-25 queries and a
  difference of two queries looks like a difference of 0.08 in a metric. Point
  estimates at that sample size invite conclusions the data does not support.

  McNemar's exact test, because every mode is run over the *same* queries. That
  is a paired design, so a two-proportion z-test is the wrong tool - it assumes
  independent samples and throws away the pairing, which is most of the
  information. McNemar looks only at the queries where the two modes disagreed,
  which is exactly the evidence that distinguishes them.

The exact binomial form is used rather than the chi-square approximation
because the discordant counts here are small (often under 10), where the
approximation is unreliable.

No scipy dependency: these are short enough to write directly, and the eval
harness should run anywhere the catalog does.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Optional, Sequence, Tuple


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def bootstrap_ci(values: Sequence[float], confidence: float = 0.95,
                 iterations: int = 10000, seed: int = 20260918
                 ) -> Tuple[float, float, float]:
    """Percentile bootstrap CI for the mean of per-query scores.

    Returns (point_estimate, low, high). Resampling is over queries, which is
    the unit that varies: the catalog and the model are fixed.
    """
    if not values:
        return 0.0, 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0], values[0]

    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iterations):
        means.append(mean([values[rng.randrange(n)] for _ in range(n)]))
    means.sort()

    tail = (1.0 - confidence) / 2.0
    low = means[int(tail * iterations)]
    high = means[min(int((1.0 - tail) * iterations), iterations - 1)]
    return mean(values), low, high


def _binomial_tail(k: int, n: int, p: float = 0.5) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
               for i in range(k + 1))


def mcnemar(a_outcomes: Sequence[float], b_outcomes: Sequence[float]) -> Dict:
    """Exact McNemar test on paired binary outcomes.

    a_outcomes and b_outcomes are per-query 0/1 results for two systems run
    over the same queries, in the same order.

    Only discordant pairs carry information: queries both systems got right,
    or both got wrong, say nothing about which is better.
    """
    if len(a_outcomes) != len(b_outcomes):
        raise ValueError("paired test needs equal-length outcome lists")

    a_only = sum(1 for a, b in zip(a_outcomes, b_outcomes) if a > b)
    b_only = sum(1 for a, b in zip(a_outcomes, b_outcomes) if b > a)
    discordant = a_only + b_only

    if discordant == 0:
        # The two systems agreed on every query; there is no evidence either
        # way, which is not the same as evidence of no difference.
        return {"a_only": 0, "b_only": 0, "n_discordant": 0, "p_value": 1.0,
                "note": "identical on every query"}

    smaller = min(a_only, b_only)
    p_value = min(1.0, 2.0 * _binomial_tail(smaller, discordant, 0.5))

    return {
        "a_only": a_only,
        "b_only": b_only,
        "n_discordant": discordant,
        "p_value": p_value,
    }


def format_ci(point: float, low: float, high: float, places: int = 3) -> str:
    return f"{point:.{places}f} [{low:.{places}f}, {high:.{places}f}]"


def roc_auc(positive_scores: Sequence[float],
            negative_scores: Sequence[float]) -> float:
    """AUC via the Mann-Whitney U relationship, ties counted as half.

    Used to ask how separable in-catalog and out-of-catalog queries are by a
    retrieval score, independently of where any threshold is placed. 0.5 means
    the score carries no information.
    """
    if not positive_scores or not negative_scores:
        return 0.5
    wins = 0.0
    for p in positive_scores:
        for n in negative_scores:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return wins / (len(positive_scores) * len(negative_scores))
