"""Load and clean NYC 311 rat sightings and borough census data.

Read only the columns we use from NYC Open Data (dataset 3q43-55fe).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

# Columns we need from the 311 CSV.
USECOLS: list[str] = [
    "Unique Key",
    "Created Date",
    "Closed Date",
    "Status",
    "Location Type",
    "Incident Zip",
    "Incident Address",
    "Borough",
    "Community Board",
    "Latitude",
    "Longitude",
]

# Date format in the NYC export.
DATE_FORMAT: str = "%m/%d/%Y %I:%M:%S %p"

# Borough names we use in the analysis.
BOROUGHS: list[str] = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]


def normalize_borough(value: object) -> str | None:
    """Clean up a borough name. Return None for unknown names.

    >>> normalize_borough("STATEN ISLAND")
    'Staten Island'
    >>> normalize_borough(" brooklyn ")
    'Brooklyn'
    >>> normalize_borough("Unspecified") is None
    True
    >>> normalize_borough(float("nan")) is None
    True
    """
    if not isinstance(value, str):
        return None
    name = value.strip().title()
    return name if name in BOROUGHS else None


def normalize_zip(value: object) -> str | None:
    """Keep five-digit NYC ZIP codes (prefixes 100–104 or 110–116).

    Handle values like 10472.0 and ZIP+4 too.

    >>> normalize_zip(10472.0)
    '10472'
    >>> normalize_zip("11204-1234")
    '11204'
    >>> normalize_zip("83") is None
    True
    >>> normalize_zip("90210") is None
    True
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    text = text.split("-")[0]
    if len(text) != 5 or not text.isdigit():
        return None
    if text[:3] in {"100", "101", "102", "103", "104"} or text[:3] in {
        "110", "111", "112", "113", "114", "115", "116"
    }:
        return text
    return None


def clean_sightings(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean dates, boroughs, ZIP codes, and addresses.

    Drop duplicate Unique Keys, add year and month, and sort by date.

    >>> raw = pd.DataFrame({
    ...     "Unique Key": [1, 1, 2],
    ...     "Created Date": ["01/02/2010 09:38:29 AM"] * 2 + ["12/13/2022 06:52:10 PM"],
    ...     "Closed Date": [None, None, "12/13/2022 06:52:10 PM"],
    ...     "Status": ["Pending", "Pending", "Closed"],
    ...     "Location Type": ["Other", "Other", "Vacant Lot"],
    ...     "Incident Zip": [11432.0, 11432.0, 10472.0],
    ...     "Incident Address": ["1  MAIN ST", "1  MAIN ST", None],
    ...     "Borough": ["QUEENS", "QUEENS", "Unspecified"],
    ...     "Community Board": ["12 QUEENS"] * 2 + ["Unspecified BRONX"],
    ...     "Latitude": [40.7, 40.7, None], "Longitude": [-73.8, -73.8, None]})
    >>> out = clean_sightings(raw)
    >>> len(out), list(out["year"]), out["Incident Address"].iloc[0]
    (2, [2010, 2022], '1 MAIN ST')
    >>> out["Borough"].isna().tolist()
    [False, True]
    """
    df = raw.copy()
    df = df.drop_duplicates(subset="Unique Key")
    df["Created Date"] = pd.to_datetime(df["Created Date"], format=DATE_FORMAT)
    df["Closed Date"] = pd.to_datetime(
        df["Closed Date"], format=DATE_FORMAT, errors="coerce"
    )
    df["Borough"] = df["Borough"].map(normalize_borough)
    df["Incident Zip"] = df["Incident Zip"].map(normalize_zip)
    df["Incident Address"] = (
        df["Incident Address"].astype("string").str.split().str.join(" ").str.upper()
    )
    df["year"] = df["Created Date"].dt.year
    df["month"] = df["Created Date"].dt.month
    return df.sort_values("Created Date").reset_index(drop=True)


def load_sightings(path: str | Path) -> pd.DataFrame:
    """Read the columns we need from the 311 CSV and clean them."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. See data/README.md for how to obtain the raw data."
        )
    raw = pd.read_csv(
        path,
        usecols=USECOLS,
        dtype={"Incident Zip": "string", "Incident Address": "string"},
    )
    return clean_sightings(raw)


def load_population(path: str | Path) -> pd.DataFrame:
    """Read borough census counts and check the borough names."""
    pop = pd.read_csv(path)
    bad = set(pop["borough"]) - set(BOROUGHS)
    if bad:
        raise ValueError(f"Unknown borough names in population file: {sorted(bad)}")
    return pop[["borough", "year", "population"]].astype(
        {"year": int, "population": int}
    )


def population_by_year(anchors: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Estimate populations between census years using a straight line.

    Outside those years, use the closest census count.

    >>> anchors = pd.DataFrame({"borough": ["Bronx", "Bronx"],
    ...                         "year": [2010, 2020], "population": [100, 200]})
    >>> population_by_year(anchors, [2010, 2015, 2023])["population"].tolist()
    [100.0, 150.0, 200.0]
    """
    rows = []
    for borough, grp in anchors.groupby("borough"):
        grp = grp.sort_values("year")
        values = np.interp(years, grp["year"], grp["population"])
        rows.extend(
            {"borough": borough, "year": y, "population": float(v)}
            for y, v in zip(years, values)
        )
    return pd.DataFrame(rows)


def file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Read the file in chunks to get its SHA-256 hash."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_records(path_a: str | Path, path_b: str | Path, key: str = "Unique Key") -> bool:
    """Check whether both CSVs have the same set of keys and row count."""
    keys_a = pd.read_csv(path_a, usecols=[key])[key]
    keys_b = pd.read_csv(path_b, usecols=[key])[key]
    return set(keys_a) == set(keys_b) and len(keys_a) == len(keys_b)
