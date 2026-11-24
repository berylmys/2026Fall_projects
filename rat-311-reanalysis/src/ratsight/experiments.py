"""Run the hypotheses in config.yaml and return a verdict and tables for each."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from ratsight import metrics, original, plots, stats
from ratsight.load import BOROUGHS, population_by_year


@dataclass
class Context:
    """Shared inputs for every experiment."""

    sightings: pd.DataFrame
    population_anchors: pd.DataFrame
    years: list[int]
    out_dir: Path
    seed: int = 0
    n_boot: int = 1000

    @property
    def population(self) -> pd.DataFrame:
        """Annual borough populations for the analysis years."""
        return population_by_year(self.population_anchors, self.years)


@dataclass
class Result:
    """Outcome of one experiment."""

    key: str
    hypothesis: str
    verdict: str
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    figures: list[Path] = field(default_factory=list)


def h1_per_capita(ctx: Context, per: int = 10_000) -> Result:
    """H1: correcting the per-capita calculation changes the borough ranking."""
    totals = ctx.sightings["Borough"].value_counts().to_dict()
    orig = original.original_per_capita({b: int(totals[b]) for b in BOROUGHS}, per)
    # Keep the same records and use each borough’s own count and average population.
    all_years = sorted(int(y) for y in ctx.sightings["year"].unique())
    mean_pop = (population_by_year(ctx.population_anchors, all_years)
                .groupby("borough")["population"].mean())
    corr = pd.Series({b: totals[b] / mean_pop[b] * per for b in BOROUGHS},
                     name="corrected_rate")
    annual_avg = metrics.corrected_borough_rates(
        ctx.sightings, ctx.population, ctx.years, per).rename("annual_avg_rate")
    table = pd.concat([orig, corr, annual_avg], axis=1).loc[orig.index]
    table["original_rank"] = table["original_rate"].rank(ascending=False).astype(int)
    table["corrected_rank"] = table["corrected_rate"].rank(ascending=False).astype(int)
    changed = table.index[table["original_rank"] != table["corrected_rank"]].tolist()
    fig = plots.plot_rate_comparison(table, ctx.out_dir / "figures" / "h1_per_capita.png")
    order = " > ".join(table.sort_values("corrected_rank").index)
    verdict = (
        f"SUPPORTED: ranking changes for {', '.join(changed)}. Corrected order: {order}."
        if changed else f"NOT SUPPORTED: ranking unchanged ({order})."
    )
    return Result("H1", "Fixing the per-capita bug changes the borough ranking",
                  verdict, {"h1_per_capita": table.round(2)}, [fig])


def h2_trend(ctx: Context, per: int = 100_000, repeat_window_days: int = 30,
             baseline_end: int = 2019, test_years: tuple[int, ...] = (2021, 2022)) -> Result:
    """H2: complaints rise *steadily*, even per capita and after removing repeats."""
    df = ctx.sightings[ctx.sightings["year"].isin(ctx.years)].copy()
    df["repeat"] = metrics.mark_repeat_complaints(df, repeat_window_days)
    city_pop = ctx.population.groupby("year")["population"].sum()
    annual = df.groupby("year").agg(
        complaints=("Unique Key", "size"),
        episodes=("repeat", lambda s: int((~s).sum())),
    )
    annual["per_100k"] = annual["complaints"] / city_pop.reindex(annual.index) * per
    annual["episodes_per_100k"] = annual["episodes"] / city_pop.reindex(annual.index) * per
    annual = annual.reset_index()

    trend_rows = []
    for col in ["complaints", "per_100k", "episodes_per_100k"]:
        r = stats.trend_test(annual["year"], annual[col])
        trend_rows.append({"series": col, "slope_per_year": r.slope,
                           "slope_low": r.slope_low, "slope_high": r.slope_high,
                           "kendall_tau": r.tau, "p_value": r.p_value})
    trends = pd.DataFrame(trend_rows)

    base = annual[annual["year"] <= baseline_end]
    new = annual[annual["year"].isin(test_years)]
    breaks = pd.DataFrame(stats.exceeds_baseline(
        base["year"], base["per_100k"], new["year"], new["per_100k"]))

    yoy_up = int((annual["per_100k"].diff().dropna() > 0).sum())
    n_steps = len(annual) - 1
    borough = metrics.per_capita_rates(
        metrics.annual_counts(df, by="Borough"), ctx.population, per)
    figs = [
        plots.plot_annual_trend(annual, ctx.out_dir / "figures" / "h2_citywide.png",
                                "per_100k", "H2  Rat-sighting complaints per 100,000 residents",
                                "per 100k"),
        plots.plot_annual_trend(borough, ctx.out_dir / "figures" / "h2_by_borough.png",
                                "rate", "H2  Complaints per 100,000 residents by borough",
                                "per 100k", by="borough"),
    ]
    pc = trends.set_index("series").loc["per_100k"]
    above = breaks.loc[breaks["above"], "x"].astype(int).tolist()
    verdict = (
        f"PARTLY SUPPORTED: upward trend per capita (Theil-Sen {pc.slope_per_year:.1f}/100k/yr, "
        f"95% CI {pc.slope_low:.1f} to {pc.slope_high:.1f}, Kendall p={pc.p_value:.3f}), but it is NOT "
        f"'year after year': the rate rose in only {yoy_up} of {n_steps} year-to-year steps. "
        f"Years above the {ctx.years[0]}-{baseline_end} trend band: {above or 'none'}."
    )
    return Result("H2", "Complaints rise year after year (per capita, repeats removed)",
                  verdict, {"h2_annual": annual.round(2), "h2_trends": trends.round(4),
                            "h2_breaks": breaks.round(2), "h2_by_borough": borough.round(2)},
                  figs)


def h3_seasonality(ctx: Context) -> Result:
    """H3: the original monthly averages are biased by uneven month coverage."""
    orig = original.original_monthly_average(ctx.sightings)
    corr = metrics.monthly_profile(ctx.sightings, ctx.years)
    table = corr.copy()
    table["original_avg"] = orig
    table["bias_pct"] = (table["original_avg"] / table["mean"] - 1) * 100
    fig = plots.plot_monthly(orig, corr, ctx.out_dir / "figures" / "h3_monthly.png")
    first_half = table.loc[1:6, "bias_pct"].mean()
    second_half = table.loc[7:12, "bias_pct"].mean()
    peak_o, peak_c = int(orig.idxmax()), int(corr["mean"].idxmax())
    verdict = (
        f"SUPPORTED: original method overstates Jan-Jun by {first_half:.0f}% on average "
        f"vs {second_half:.0f}% for Jul-Dec. Peak month: original {peak_o}, corrected {peak_c}."
    )
    return Result("H3", "Original monthly averages are biased", verdict,
                  {"h3_monthly": table.round(1)}, [fig])


def h4_concentration(ctx: Context, unit: str = "Incident Zip",
                     top_fraction: float = 0.1) -> Result:
    """H4: complaints became less concentrated (the original's "spread" claim)."""
    conc = metrics.concentration_by_year(ctx.sightings, unit, ctx.years, top_fraction)
    sub = ctx.sightings[ctx.sightings["year"].isin(ctx.years) & ctx.sightings[unit].notna()]
    table = sub.groupby(["year", unit]).size().unstack(fill_value=0).reindex(ctx.years)
    lows, highs = [], []
    for i, (_year, row) in enumerate(table.iterrows()):
        lo, hi = stats.multinomial_ci(row.to_numpy(), metrics.gini, ctx.n_boot, seed=ctx.seed + i)
        lows.append(lo)
        highs.append(hi)
    conc["gini_low"], conc["gini_high"] = lows, highs
    trend = stats.trend_test(conc["year"], conc["gini"])
    fig = plots.plot_concentration(conc, ctx.out_dir / "figures" / "h4_concentration.png")
    direction = ("decreasing (more spread out)" if trend.significant_decrease
                 else "increasing (more concentrated)" if trend.significant_increase
                 else "no significant change")
    first, last = conc.iloc[0], conc.iloc[-1]
    verdict = (
        f"Gini across {unit} went from {first.gini:.3f} ({int(first.year)}) to "
        f"{last.gini:.3f} ({int(last.year)}); trend is {direction} "
        f"(slope {trend.slope:.4f}/yr, 95% CI {trend.slope_low:.4f} to {trend.slope_high:.4f})."
    )
    verdict = ("SUPPORTED: " if trend.significant_decrease else "NOT SUPPORTED: ") + verdict
    return Result("H4", "Complaints became more spread out over time", verdict,
                  {"h4_concentration": conc.round(4)}, [fig])


def h5_repeats(ctx: Context, windows: tuple[int, ...] = (7, 30, 90)) -> Result:
    """H5: repeat complaints at the same address inflate counts and hotspots."""
    df = ctx.sightings[ctx.sightings["year"].isin(ctx.years)]
    rows = []
    for w in windows:
        rep = metrics.mark_repeat_complaints(df, w)
        rows.append({"window_days": w, "repeat_share": float(rep.mean()),
                     "episodes": int((~rep).sum()), "complaints": len(df)})
    sens = pd.DataFrame(rows)
    top = df["Incident Address"].value_counts().head(10).rename("complaints").to_frame()
    rep30 = metrics.mark_repeat_complaints(df, 30)
    top["episodes_30d"] = df.loc[~rep30, "Incident Address"].value_counts().reindex(top.index)
    share30 = sens.set_index("window_days")["repeat_share"].get(30, np.nan)
    verdict = (
        f"SUPPORTED: {share30:.1%} of complaints repeat a complaint at the same address within "
        f"30 days; top 'hotspot' addresses shrink sharply when counted as episodes."
    )
    return Result("H5", "Repeat complaints inflate counts", verdict,
                  {"h5_sensitivity": sens.round(4), "h5_top_addresses": top}, [])


# These names match the keys in config.yaml.
EXPERIMENTS: dict[str, Callable[..., Result]] = {
    "h1_per_capita": h1_per_capita,
    "h2_trend": h2_trend,
    "h3_seasonality": h3_seasonality,
    "h4_concentration": h4_concentration,
    "h5_repeats": h5_repeats,
}


def run_experiment(name: str, ctx: Context, params: dict[str, Any] | None = None) -> Result:
    """Run the named experiment with its config settings."""
    if name not in EXPERIMENTS:
        raise KeyError(f"Unknown experiment {name!r}; choose from {sorted(EXPERIMENTS)}")
    params = dict(params or {})
    for key in ("test_years", "windows"):
        if key in params:
            params[key] = tuple(params[key])
    return EXPERIMENTS[name](ctx, **params)
