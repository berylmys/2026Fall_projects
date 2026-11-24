"""Trend tests and confidence intervals using NumPy and SciPy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class TrendResult:
    """Store the results of a yearly trend test."""

    slope: float
    slope_low: float
    slope_high: float
    tau: float
    p_value: float

    @property
    def significant_increase(self) -> bool:
        """True when the whole 95% slope interval is above zero."""
        return self.slope_low > 0

    @property
    def significant_decrease(self) -> bool:
        """True when the whole 95% slope interval is below zero."""
        return self.slope_high < 0


def trend_test(x: np.ndarray | list[float], y: np.ndarray | list[float]) -> TrendResult:
    """Estimate the Theil-Sen slope and run a Mann-Kendall trend test.

    >>> r = trend_test([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6])
    >>> r.slope, r.significant_increase
    (1.0, True)
    """
    x_arr, y_arr = np.asarray(x, float), np.asarray(y, float)
    if x_arr.size < 3:
        raise ValueError("Need at least 3 points for a trend test.")
    slope, _intercept, low, high = stats.theilslopes(y_arr, x_arr, alpha=0.95)
    tau, p_value = stats.kendalltau(x_arr, y_arr)
    return TrendResult(float(slope), float(low), float(high), float(tau), float(p_value))


def exceeds_baseline(
    x_base: np.ndarray | list[float],
    y_base: np.ndarray | list[float],
    x_new: np.ndarray | list[float],
    y_new: np.ndarray | list[float],
    z: float = 1.96,
) -> list[dict[str, float | bool]]:
    """Check new values against the earlier Theil-Sen trend.

    Use z residual standard deviations on each side as a rough range.

    >>> out = exceeds_baseline([0, 1, 2, 3], [0, 1, 2, 3], [4, 5], [4, 50])
    >>> [row["above"] for row in out]
    [False, True]
    """
    xb, yb = np.asarray(x_base, float), np.asarray(y_base, float)
    slope, intercept, _lo, _hi = stats.theilslopes(yb, xb)
    resid = yb - (intercept + slope * xb)
    sd = float(np.std(resid, ddof=1)) if resid.size > 1 else 0.0
    rows: list[dict[str, float | bool]] = []
    for xv, yv in zip(np.asarray(x_new, float), np.asarray(y_new, float)):
        pred = intercept + slope * xv
        upper, lower = pred + z * sd, pred - z * sd
        rows.append(
            {"x": float(xv), "observed": float(yv), "predicted": float(pred),
             "upper": float(upper), "lower": float(lower), "above": bool(yv > upper)}
        )
    return rows


def bootstrap_ci(
    data: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    n_boot: int = 1000,
    level: float = 0.95,
    seed: int | None = 0,
) -> tuple[float, float]:
    """Resample rows with replacement to get a percentile confidence interval.

    >>> lo, hi = bootstrap_ci(np.arange(100.0), np.mean, n_boot=500, seed=1)
    >>> 40 < lo < 49.5 < hi < 59
    True
    """
    rng = np.random.default_rng(seed)
    arr = np.asarray(data)
    n = arr.shape[0]
    draws = np.empty(n_boot)
    for i in range(n_boot):
        draws[i] = statistic(arr[rng.integers(0, n, n)])
    alpha = (1 - level) / 2
    return float(np.quantile(draws, alpha)), float(np.quantile(draws, 1 - alpha))


def multinomial_ci(
    counts: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    n_boot: int = 1000,
    level: float = 0.95,
    seed: int | None = 0,
) -> tuple[float, float]:
    """Get a confidence interval by simulating new counts.

    Keep the original total and use the observed proportions as probabilities.

    >>> lo, hi = multinomial_ci(np.array([50, 50]), lambda c: c[0] / c.sum(), seed=3)
    >>> 0.35 < lo < 0.5 < hi < 0.65
    True
    """
    rng = np.random.default_rng(seed)
    counts = np.asarray(counts, dtype=int)
    total = counts.sum()
    probs = counts / total
    draws = np.array([statistic(rng.multinomial(total, probs)) for _ in range(n_boot)])
    alpha = (1 - level) / 2
    return float(np.quantile(draws, alpha)), float(np.quantile(draws, 1 - alpha))
