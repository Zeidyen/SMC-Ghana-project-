"""
Time-series (monthly) clinical-incidence trajectories from the 20k projection:
BAU (4-cycle baseline continued) vs each SMC scenario, per age band, with the
2023 projection fork marked. Mean across seeds; 95% CI ribbon on BAU and the
full package. Shows both the widening gap and the seasonal SMC suppression.

    python timeseries.py <region> [severe]
"""
import os
import sys
import glob
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 18})

import manifest
import historical as H

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"baseline": "BAU: SMC-4 (U5)", "5cycle": "SMC-5 (U5)", "age10": "SMC-4 (U10)",
          "age15": "SMC-4 (U15)", "5cycle_age10": "SMC-5 (U10)", "5cycle_age15": "SMC-5 (U15)"}
# distinct categorical colours (one per scenario) for legibility of the line plot
COLORS = {"baseline": "#000000", "5cycle": "#ff7f0e", "age10": "#1f77b4",
          "age15": "#2ca02c", "5cycle_age10": "#9467bd", "5cycle_age15": "#d62728"}
FOUR_CYCLE = set()   # no linestyle distinction; colour alone separates scenarios
SEEDS = list(range(1, 61))
BANDS = {"U5": [0], "5-10": [1], "10-15": [2], "U15": [0, 1, 2]}
X0 = 2019          # first year to display (context before the 2023 fork)


def load(region, field):
    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    # series[scen][band] = list over seeds of (times, values)
    series = {sc: {b: [] for b in BANDS} for sc in SCENARIOS}
    for entry in os.scandir(exp):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; sr = json.load(open(rep))
        arr = np.array(sr["DataByTimeAndAgeBins"][field])
        pop = np.array(sr["DataByTimeAndAgeBins"]["Average Population by Age Bin"])
        tt = np.array(sr["DataByTime"]["Time Of Report"][:len(arr)])
        yrs = base + pd.to_timedelta(tt, unit="D")
        yfrac = yrs.year + (yrs.dayofyear - 1) / 365.25
        for b, idx in BANDS.items():
            # pop-weighted group rate (cases/pop); correct for multi-bin U15, and
            # reduces to the plain rate for single bins
            rate = 1000 * (arr[:, idx] * pop[:, idx]).sum(axis=1) / pop[:, idx].sum(axis=1)
            series[tg["scen"]][b].append((yfrac, rate))
    return series


def grid(series):
    # mean/CI across seeds per scenario/band on a common time axis. Seeds share
    # the same reporting cadence; interpolate onto the reference grid to be safe.
    out = {sc: {} for sc in SCENARIOS}
    ref = series["baseline"]["U5"][0][0]
    tg = ref[ref >= X0]
    for sc in SCENARIOS:
        for b in BANDS:
            stack = np.vstack([np.interp(tg, v_t, v) for (v_t, v) in series[sc][b]])
            out[sc][b] = (tg, stack.mean(axis=0),
                          np.percentile(stack, 2.5, axis=0), np.percentile(stack, 97.5, axis=0))
    return out


def plot(region, field="Annual Clinical Incidence by Age Bin", tag="clinical"):
    g = grid(load(region, field))
    ribbon = {"baseline", "5cycle_age15"}     # CI bands only on BAU + full package (clarity)
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), sharex=True)
    for ax, b in zip(axes.ravel(), BANDS):
        for sc in SCENARIOS:
            tg, m, lo, hi = g[sc][b]
            if sc == "baseline":
                # BAU spans the whole period: pre-2023 IS the shared history for every
                # scenario, so only BAU is drawn there; scenarios branch off at 2023.
                sel = np.ones_like(tg, dtype=bool)
            else:
                sel = tg >= 2023                       # scenarios only after the fork
            lw = 1.8 if sc in ("baseline", "5cycle_age15") else 1.1
            ls = "--" if sc in FOUR_CYCLE else "-"
            ax.plot(tg[sel], m[sel], color=COLORS[sc], lw=lw, ls=ls, label=LABELS[sc], zorder=3 if sc in ribbon else 2)
            if sc in ribbon:
                ax.fill_between(tg[sel], lo[sel], hi[sel], color=COLORS[sc], alpha=0.12, zorder=1)
        ax.axvline(2023, ls="--", color="grey", lw=1)
        ax.text(2023.05, ax.get_ylim()[1] * 0.95, "← shared history | scenarios →", color="grey", fontsize=7.5, va="top")
        ax.set_title(f"{b}")
        ax.set_ylabel(f"{tag} cases /1000/yr")
    axes.ravel()[0].legend(fontsize=8, ncol=2, loc="upper left")
    fig.suptitle(f"{region}: {tag} incidence — shared history to 2022, then BAU vs SMC scenarios 2023-27 (monthly mean, 2k, 60 seeds)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = f"data/timeseries_{tag}_{region}.png"; fig.savefig(out, dpi=130); print("saved", out)


if __name__ == "__main__":
    region = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "severe":
        plot(region, "Annual Severe Incidence by Age Bin", "severe")
    else:
        plot(region, "Annual Clinical Incidence by Age Bin", "clinical")
