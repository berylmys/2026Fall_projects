"""Tests for ratsight.metrics, ratsight.stats and ratsight.original."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ratsight import load, metrics, original, stats


@pytest.fixture
def df(raw_df):
    return load.clean_sightings(raw_df)


def test_complete_years_excludes_partial(df):
    assert metrics.complete_years(df) == [2015, 2016, 2017, 2018, 2019]


def test_annual_counts(df):
    counts = metrics.annual_counts(df).set_index("year")["count"]
    assert counts[2017] == 140
    by = metrics.annual_counts(df, by="Borough")
    assert by.groupby("year")["count"].sum()[2017] == 140


def test_corrected_rates_use_own_population(df, population_path):
    anchors = load.load_population(population_path)
    years = [2015, 2016]
    pop = load.population_by_year(anchors, years)
    rates = metrics.corrected_borough_rates(df, pop, years, per=10_000)
    # With equal counts, the smallest borough has the highest rate.
    assert rates.index[0] == "Staten Island"
    assert rates.index[-1] == "Brooklyn"


def test_monthly_profile_shape(df):
    prof = metrics.monthly_profile(df, [2015, 2016, 2017])
    assert list(prof.index) == list(range(1, 13))
    assert prof["n_years"].iloc[0] == 3
    assert np.isclose(prof["mean"].sum() * 3, 100 + 120 + 140)


def test_repeat_complaints_ignore_other_zip():
    d = pd.DataFrame({
        "Incident Address": ["1 A ST", "1 A ST"],
        "Incident Zip": ["10001", "11201"],
        "Created Date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
    })
    assert not metrics.mark_repeat_complaints(d, 30).any()


def test_gini_bounds():
    assert metrics.gini([]) == 0.0
    assert metrics.gini([0, 0]) == 0.0
    assert 0 < metrics.gini([1, 2, 3, 10]) < 1


def test_concentration_by_year_counts_zero_units():
    d = pd.DataFrame({"year": [2020, 2020, 2021], "Incident Zip": ["a", "b", "a"]})
    out = metrics.concentration_by_year(d, "Incident Zip", [2020, 2021]).set_index("year")
    assert out.loc[2020, "gini"] == 0.0
    assert out.loc[2021, "n_units"] == 1
    assert out.loc[2021, "gini"] > 0


def test_original_bug_matches_published_csv():
    """Check the rates against the CSV in the original repo."""
    totals = {"Brooklyn": 79778, "Manhattan": 58366, "Bronx": 40563,
              "Queens": 32878, "Staten Island": 8913}
    rates = original.original_per_capita(totals)
    assert rates["Manhattan"] == pytest.approx(239.41552934010366)
    assert rates["Bronx"] == pytest.approx(223.25678672654948)
    # Manhattan's own count would give a much higher rate.
    assert totals["Manhattan"] / original.ORIGINAL_POPULATION["Manhattan"] * 1e4 > 340


def test_original_monthly_divides_by_12(df):
    avg = original.original_monthly_average(df)
    assert avg.sum() * 12 == len(df)


def test_trend_detects_decrease_and_rejects_short():
    r = stats.trend_test([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
    assert r.significant_decrease and not r.significant_increase
    with pytest.raises(ValueError):
        stats.trend_test([1, 2], [1, 2])


def test_exceeds_baseline_flags_low_values():
    out = stats.exceeds_baseline([0, 1, 2, 3, 4], [0, 1.1, 1.9, 3.2, 4], [5], [-10])
    assert out[0]["observed"] < out[0]["lower"]
    assert not out[0]["above"]


def test_bootstrap_ci_is_reproducible():
    data = np.random.default_rng(0).normal(size=200)
    assert stats.bootstrap_ci(data, np.mean, 300, seed=5) == stats.bootstrap_ci(
        data, np.mean, 300, seed=5)
