"""Make a small set of fake 311 records for the tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ratsight.load import BOROUGHS, USECOLS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def make_raw(n_per_year: dict[int, int], seed: int = 0, end_month: int = 12) -> pd.DataFrame:
    """Make test data in the same format as the NYC export."""
    rng = np.random.default_rng(seed)
    rows = []
    key = 1
    last_year = max(n_per_year)
    for year, n in n_per_year.items():
        months = end_month if year == last_year else 12
        for i in range(n):
            if i == 0:
                ts = pd.Timestamp(year, 1, 1, 9)
            elif i == 1:
                ts = pd.Timestamp(year, months, 28 if months < 12 else 31, 9)
            else:
                ts = pd.Timestamp(year, int(rng.integers(1, months + 1)),
                                  int(rng.integers(1, 29)), int(rng.integers(0, 24)))
            borough = BOROUGHS[i % 5]
            rows.append({
                "Unique Key": key,
                "Created Date": ts.strftime("%m/%d/%Y %I:%M:%S %p"),
                "Closed Date": None,
                "Status": "Closed",
                "Location Type": "3+ Family Apt. Building",
                "Incident Zip": f"{10001 + (i % 7)}",
                "Incident Address": f"{i % 40} TEST STREET",
                "Borough": borough.upper(),
                "Community Board": f"01 {borough.upper()}",
                "Latitude": 40.7,
                "Longitude": -73.9,
            })
            key += 1
    return pd.DataFrame(rows, columns=USECOLS)


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """Five complete years (2015-2019) plus a partial 2020 ending in June."""
    return make_raw({2015: 100, 2016: 120, 2017: 140, 2018: 160, 2019: 180, 2020: 90},
                    end_month=6)


@pytest.fixture
def csv_path(tmp_path: Path, raw_df: pd.DataFrame) -> Path:
    """Save the fake records as a CSV."""
    path = tmp_path / "sightings.csv"
    raw_df.to_csv(path, index=False)
    return path


@pytest.fixture
def population_path() -> Path:
    """Load the census counts included with the project."""
    return ROOT / "data" / "population_boroughs.csv"
