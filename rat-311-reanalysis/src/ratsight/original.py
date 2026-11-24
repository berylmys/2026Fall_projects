"""Redo the original notebook’s calculations for comparison.

Source: https://github.com/federicodt/nyc-rat-health-problem
"""

from __future__ import annotations

import pandas as pd

# Cell 36 mixed population counts from 2010 and 2020.
ORIGINAL_POPULATION: dict[str, int] = {
    "Manhattan": 1694251,  # 2020 census
    "Bronx": 1472654,  # 2020 census
    "Brooklyn": 2736074,  # 2020 census
    "Staten Island": 468730,  # 2010 census
    "Queens": 2230722,  # 2010 census
}

# Cell 36 used Bronx counts for Manhattan and Queens counts for the Bronx.
ORIGINAL_NUMERATOR_SOURCE: dict[str, str] = {
    "Manhattan": "Bronx",
    "Bronx": "Queens",
    "Brooklyn": "Brooklyn",
    "Staten Island": "Staten Island",
    "Queens": "Queens",
}


def original_per_capita(totals: dict[str, int], per: int = 10_000) -> pd.Series:
    """Redo the original complaints-per-10,000 calculation from cell 36.

    >>> totals = {"Brooklyn": 79778, "Manhattan": 58366, "Bronx": 40563,
    ...           "Queens": 32878, "Staten Island": 8913}
    >>> original_per_capita(totals).round(2).to_dict()
    {'Brooklyn': 291.58, 'Manhattan': 239.42, 'Bronx': 223.26, 'Staten Island': 190.15, 'Queens': 147.39}
    """
    rates = {
        borough: totals[ORIGINAL_NUMERATOR_SOURCE[borough]] / pop * per
        for borough, pop in ORIGINAL_POPULATION.items()
    }
    return pd.Series(rates, name="original_rate").sort_values(ascending=False)


def original_monthly_average(df: pd.DataFrame) -> pd.Series:
    """Redo the monthly average from cell 87.

    The notebook divided every month’s total by 12, even though
    January through June had one extra year of data.
    """
    return (df["month"].value_counts() / 12).sort_index()
