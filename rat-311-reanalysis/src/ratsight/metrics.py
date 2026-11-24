"""Calculate complaint rates, repeat counts, and concentration."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ratsight.load import BOROUGHS


def complete_years(df: pd.DataFrame, slack_days: int = 7) -> list[int]:
    """Find the full years covered by the data.

    Allow up to slack_days at either end of each year.

    >>> d = pd.DataFrame({"Created Date": pd.to_datetime(
    ...     ["2010-01-01", "2011-06-01", "2012-12-30", "2013-06-25"])})
    >>> d["year"] = d["Created Date"].dt.year
    >>> complete_years(d)
    [2010, 2011, 2012]
    """
    start, end = df["Created Date"].min(), df["Created Date"].max()
    years = []
    for year in sorted(df["year"].unique()):
        first_ok = start <= pd.Timestamp(year, 1, 1) + pd.Timedelta(days=slack_days)
        last_ok = end >= pd.Timestamp(year, 12, 31) - pd.Timedelta(days=slack_days)
        if first_ok and last_ok:
            years.append(int(year))
    return years


def annual_counts(df: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    """Count complaints by year, with an optional split by borough or another column."""
    keys = ["year"] if by is None else ["year", by]
    return df.groupby(keys, dropna=True).size().reset_index(name="count")


def per_capita_rates(
    counts: pd.DataFrame, population: pd.DataFrame, per: int = 10_000
) -> pd.DataFrame:
    """Match each borough and year with its population to get the complaint rate."""
    merged = counts.rename(columns={"Borough": "borough"}).merge(
        population, on=["borough", "year"], how="inner"
    )
    merged["rate"] = merged["count"] / merged["population"] * per
    return merged


def corrected_borough_rates(
    df: pd.DataFrame, population: pd.DataFrame, years: list[int], per: int = 10_000
) -> pd.Series:
    """Use each borough’s own count and population to get its yearly rate.

    Average those rates across the selected years.
    """
    sub = df[df["year"].isin(years)]
    rates = per_capita_rates(annual_counts(sub, by="Borough"), population, per)
    return (
        rates.groupby("borough")["rate"].mean().reindex(BOROUGHS)
        .rename("corrected_rate").sort_values(ascending=False)
    )


def monthly_profile(df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Summarize counts for each month across the selected years.

    Fill missing month counts with zero.
    """
    sub = df[df["year"].isin(years)]
    table = sub.groupby(["year", "month"]).size().unstack(fill_value=0)
    table = table.reindex(index=years, columns=range(1, 13), fill_value=0)
    return pd.DataFrame(
        {
            "mean": table.mean(),
            "std": table.std(ddof=1),
            "min": table.min(),
            "max": table.max(),
            "n_years": len(years),
        }
    )


def mark_repeat_complaints(df: pd.DataFrame, window_days: int = 30) -> pd.Series:
    """Flag a repeat if the last complaint at the same address and ZIP
    was within window_days. Skip rows with no address.

    >>> d = pd.DataFrame({
    ...     "Incident Address": ["1 A ST", "1 A ST", "1 A ST", None],
    ...     "Incident Zip": ["10001"] * 4,
    ...     "Created Date": pd.to_datetime(
    ...         ["2020-01-01", "2020-01-10", "2020-06-01", "2020-01-02"])})
    >>> mark_repeat_complaints(d, window_days=30).tolist()
    [False, True, False, False]
    """
    has_addr = df["Incident Address"].notna()
    keyed = df.loc[has_addr, ["Incident Address", "Incident Zip", "Created Date"]]
    keyed = keyed.assign(zip_key=keyed["Incident Zip"].fillna("?"))
    keyed = keyed.sort_values("Created Date")
    gaps = keyed.groupby(["Incident Address", "zip_key"])["Created Date"].diff()
    repeat = gaps <= pd.Timedelta(days=window_days)
    out = pd.Series(False, index=df.index)
    out.loc[repeat.index] = repeat.to_numpy()
    return out


def gini(values: np.ndarray | list[float]) -> float:
    """Measure how uneven the counts are. Zero means all counts are equal.

    >>> gini([5, 5, 5, 5])
    0.0
    >>> round(gini([0, 0, 0, 10]), 2)
    0.75
    """
    arr = np.sort(np.asarray(values, dtype=float))
    if arr.size == 0 or arr.sum() == 0:
        return 0.0
    n = arr.size
    ranks = np.arange(1, n + 1)
    return float((2 * np.sum(ranks * arr) / (n * arr.sum())) - (n + 1) / n)


def top_share(values: np.ndarray | list[float], fraction: float = 0.1) -> float:
    """Find how much of the total comes from the highest counts.

    >>> top_share([1, 1, 1, 1, 1, 1, 1, 1, 1, 91], fraction=0.1)
    0.91
    """
    arr = np.sort(np.asarray(values, dtype=float))[::-1]
    k = max(1, int(round(fraction * arr.size)))
    total = arr.sum()
    return float(arr[:k].sum() / total) if total else 0.0


def concentration_by_year(
    df: pd.DataFrame, unit: str, years: list[int], top_fraction: float = 0.1
) -> pd.DataFrame:
    """Measure how concentrated complaints are each year.

    Use the same set of areas every year and fill missing counts with zero.
    """
    sub = df[df["year"].isin(years) & df[unit].notna()]
    table = sub.groupby(["year", unit]).size().unstack(fill_value=0)
    table = table.reindex(index=years, fill_value=0)
    rows = [
        {
            "year": year,
            "gini": gini(row.to_numpy()),
            "top_share": top_share(row.to_numpy(), top_fraction),
            "n_units": int((row > 0).sum()),
            "total": int(row.sum()),
        }
        for year, row in table.iterrows()
    ]
    return pd.DataFrame(rows)
