"""Tests for ratsight.load."""

from __future__ import annotations

import pandas as pd
import pytest

from ratsight import load


def test_load_sightings_parses_and_cleans(csv_path):
    df = load.load_sightings(csv_path)
    assert pd.api.types.is_datetime64_any_dtype(df["Created Date"])
    assert set(df["Borough"].dropna()) == set(load.BOROUGHS)
    assert df["Created Date"].is_monotonic_increasing
    assert {"year", "month"} <= set(df.columns)


def test_load_sightings_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="data/README.md"):
        load.load_sightings(tmp_path / "nope.csv")


def test_clean_drops_duplicate_keys(raw_df):
    doubled = pd.concat([raw_df, raw_df.head(5)])
    assert len(load.clean_sightings(doubled)) == len(raw_df)


@pytest.mark.parametrize("value, expected", [
    ("10472", "10472"), (11204.0, "11204"), ("N/A", None), ("07302", None), (None, None),
])
def test_normalize_zip(value, expected):
    assert load.normalize_zip(value) == expected


def test_population_interpolation_and_hold(population_path):
    anchors = load.load_population(population_path)
    pop = load.population_by_year(anchors, [2010, 2015, 2020, 2022])
    bronx = pop[pop["borough"] == "Bronx"].set_index("year")["population"]
    assert bronx[2010] == 1385108
    assert bronx[2020] == bronx[2022] == 1472654  # same as the last census
    assert bronx[2010] < bronx[2015] < bronx[2020]


def test_load_population_rejects_bad_names(tmp_path):
    bad = tmp_path / "pop.csv"
    bad.write_text("borough,year,population,source\nKings,2010,1,x\n")
    with pytest.raises(ValueError, match="Kings"):
        load.load_population(bad)


def test_same_records_and_hash(tmp_path, raw_df):
    a, b, c = tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "c.csv"
    raw_df.to_csv(a, index=False)
    raw_df.iloc[::-1].to_csv(b, index=False)  # same records, different order
    raw_df.head(10).to_csv(c, index=False)
    assert load.same_records(a, b)
    assert not load.same_records(a, c)
    assert load.file_sha256(a) != load.file_sha256(b)  # same records in a different order
