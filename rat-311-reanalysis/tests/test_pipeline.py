"""End-to-end tests: every experiment and the config-driven runner."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ratsight import experiments, load, metrics, run


@pytest.fixture
def ctx(raw_df, population_path, tmp_path):
    df = load.clean_sightings(raw_df)
    return experiments.Context(df, load.load_population(population_path),
                               metrics.complete_years(df), tmp_path, seed=1, n_boot=50)


@pytest.mark.parametrize("name", sorted(experiments.EXPERIMENTS))
def test_each_experiment_runs(ctx, name):
    params = {"h2_trend": {"baseline_end": 2017, "test_years": [2018, 2019]}}.get(name)
    result = experiments.run_experiment(name, ctx, params)
    assert result.verdict
    assert result.tables
    for fig in result.figures:
        assert Path(fig).exists()


def test_h2_finds_increase(ctx):
    res = experiments.run_experiment(
        "h2_trend", ctx, {"baseline_end": 2017, "test_years": [2018, 2019]})
    trends = res.tables["h2_trends"].set_index("series")
    assert trends.loc["complaints", "slope_low"] > 0


def test_unknown_experiment(ctx):
    with pytest.raises(KeyError):
        experiments.run_experiment("h99", ctx)


def test_runner_end_to_end(tmp_path, csv_path, population_path):
    cfg = {
        "data": {"sightings_csv": str(csv_path), "population_csv": str(population_path),
                 "duplicate_check_csv": str(csv_path)},
        "output_dir": "out",
        "years": "complete",
        "n_boot": 30,
        "experiments": {"h1_per_capita": {}, "h3_seasonality": {},
                        "h5_repeats": {"windows": [30]}},
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    results = run.main(["--config", str(cfg_path)])
    assert [r.key for r in results] == ["H1", "H3", "H5"]
    summary = (tmp_path / "out" / "summary.md").read_text()
    assert "identical records" in summary and "True" in summary
    assert (tmp_path / "out" / "tables" / "h1_per_capita.csv").exists()


def test_project_config_is_valid():
    cfg = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.yaml").read_text())
    assert set(cfg["experiments"]) <= set(experiments.EXPERIMENTS)
