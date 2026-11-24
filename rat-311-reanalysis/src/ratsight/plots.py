"""Make PNG plots for the report. Keep each borough the same color."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ratsight.load import BOROUGHS  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
BOROUGH_COLORS: dict[str, str] = dict(zip(BOROUGHS, SERIES))
TEXT, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"


def _style(ax: plt.Axes, title: str, ylabel: str) -> None:
    """Give the plot the same style as the others."""
    ax.set_title(title, loc="left", fontsize=13, color=TEXT, pad=12)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED, length=0)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig: plt.Figure, path: Path) -> Path:
    """Save and close a figure, creating the parent folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_rate_comparison(table: pd.DataFrame, path: Path) -> Path:
    """Compare the old and corrected rates in a grouped bar chart.

    The table has one row per borough with original_rate and corrected_rate.
    """
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(table))
    width = 0.38
    ax.bar([i - width / 2 for i in x], table["original_rate"], width,
           color=SERIES[0], label="Original (buggy) calculation")
    ax.bar([i + width / 2 for i in x], table["corrected_rate"], width,
           color=SERIES[1], label="Corrected (own count / own population)")
    ax.set_xticks(list(x), table.index)
    ax.legend(frameon=False, labelcolor=TEXT)
    _style(ax, "H1  Complaints per 10,000 residents by borough, 2010 - Jun 2023",
           "complaints per 10,000")
    return _save(fig, path)


def plot_annual_trend(series: pd.DataFrame, path: Path, value: str, title: str,
                      ylabel: str, by: str | None = None) -> Path:
    """Line chart of an annual series, optionally one line per borough."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if by is None:
        ax.plot(series["year"], series[value], color=SERIES[0], linewidth=2,
                marker="o", markersize=5)
    else:
        for name, grp in series.groupby(by):
            ax.plot(grp["year"], grp[value], color=BOROUGH_COLORS.get(name, MUTED),
                    linewidth=2, marker="o", markersize=4, label=name)
        ax.legend(frameon=False, ncol=5, fontsize=8, labelcolor=TEXT,
                  loc="upper left")
    _style(ax, title, ylabel)
    return _save(fig, path)


def plot_monthly(original: pd.Series, corrected: pd.DataFrame, path: Path) -> Path:
    """Original monthly average vs corrected mean with min-max range."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    months = list(range(1, 13))
    ax.fill_between(months, corrected["min"], corrected["max"], color=SERIES[1],
                    alpha=0.15, linewidth=0, label="Corrected: min-max across years")
    ax.plot(months, corrected["mean"], color=SERIES[1], linewidth=2, marker="o",
            markersize=5, label="Corrected: mean of complete years")
    ax.plot(months, original.reindex(months), color=SERIES[0], linewidth=2,
            linestyle="--", marker="s", markersize=5, label="Original: total / 12")
    ax.set_xticks(months, ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.set_ylim(bottom=0, top=float(corrected["max"].max()) * 1.35)
    ax.legend(frameon=False, labelcolor=TEXT, loc="upper left", ncol=2, fontsize=8)
    _style(ax, "H3  Complaints per month", "complaints")
    return _save(fig, path)


def plot_concentration(conc: pd.DataFrame, path: Path) -> Path:
    """Gini coefficient across ZIP codes per year with bootstrap interval."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.fill_between(conc["year"], conc["gini_low"], conc["gini_high"],
                    color=SERIES[0], alpha=0.2, linewidth=0, label="95% interval")
    ax.plot(conc["year"], conc["gini"], color=SERIES[0], linewidth=2, marker="o",
            markersize=5, label="Gini across ZIP codes")
    ax.legend(frameon=False, labelcolor=TEXT)
    _style(ax, "H4  Spatial concentration of complaints (higher = more concentrated)",
           "Gini")
    return _save(fig, path)
