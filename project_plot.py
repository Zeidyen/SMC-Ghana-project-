"""
Two-panel projection figure from the existing runs (no re-sim):
  (left)  ABSOLUTE clinical incidence per 1000/yr by age band -- baseline + all
          scenarios side by side, so the starting burden is visible.
  (right) % reduction vs baseline (paired by seed).
Both with 95% CIs across seeds.

    python project_plot.py <region>
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

import manifest
import historical as H

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"baseline": "BAU: SMC-4 (U5)", "5cycle": "SMC-5 (U5)", "age10": "SMC-4 (U10)",
          "age15": "SMC-4 (U15)", "5cycle_age10": "SMC-5 (U10)", "5cycle_age15": "SMC-5 (U15)"}
SEEDS = list(range(1, 61))
PROJ_YEARS = 5
BANDS = {"U5": [0], "5-10": [1], "10-15": [2]}
COLORS = {"U5": "#d62728", "5-10": "#1f77b4", "10-15": "#2ca02c"}


def load(region):
    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    inc = {sc: {} for sc in SCENARIOS}     # inc[scen][seed][band] = incidence per person-yr
    for entry in os.scandir(exp):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; sr = json.load(open(rep))
        clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])
        tt = sr["DataByTime"]["Time Of Report"][:len(clin)]
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        proj = (yr >= 2023) & (yr <= 2022 + PROJ_YEARS)
        inc[tg["scen"]][int(tg["seed"])] = {b: clin[proj][:, idx].sum(axis=1).mean() for b, idx in BANDS.items()}
    return inc


def stat(vals):
    v = np.array(vals); return v.mean(), *np.percentile(v, [2.5, 97.5])


def plot(region):
    inc = load(region)
    seeds = [s for s in SEEDS if all(s in inc[sc] for sc in SCENARIOS)]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 5.6))
    x = np.arange(len(SCENARIOS)); w = 0.26

    # LEFT: absolute clinical incidence per 1000/yr, baseline + scenarios
    for i, b in enumerate(BANDS):
        m, lo, hi = [], [], []
        for sc in SCENARIOS:
            mu, l, h = stat([1000 * inc[sc][s][b] for s in seeds])
            m.append(mu); lo.append(mu - l); hi.append(h - mu)
        axL.bar(x + (i - 1) * w, m, w, yerr=[lo, hi], capsize=3, color=COLORS[b], label=b)
    axL.set_xticks(x); axL.set_xticklabels([LABELS[s] for s in SCENARIOS], rotation=20, ha="right", fontsize=8.5)
    axL.set_ylabel("clinical cases per 1000 children per year")
    axL.set_title("Absolute burden by age band (baseline included)")
    axL.legend(title="age band"); axL.grid(axis="y", alpha=0.3)

    # RIGHT: % reduction vs baseline (paired), scenarios only
    scen_p = [s for s in SCENARIOS if s != "baseline"]; xr = np.arange(len(scen_p))
    for i, b in enumerate(BANDS):
        m, lo, hi = [], [], []
        for sc in scen_p:
            red = [100 * (inc["baseline"][s][b] - inc[sc][s][b]) / inc["baseline"][s][b] for s in seeds]
            mu, l, h = stat(red); m.append(mu); lo.append(mu - l); hi.append(h - mu)
        axR.bar(xr + (i - 1) * w, m, w, yerr=[lo, hi], capsize=3, color=COLORS[b], label=b)
    axR.axhline(0, color="k", lw=0.8)
    axR.set_xticks(xr); axR.set_xticklabels([LABELS[s] for s in scen_p], rotation=20, ha="right", fontsize=8.5)
    axR.set_ylabel("% reduction in clinical incidence vs baseline")
    axR.set_title("Relative effect vs baseline"); axR.legend(title="age band"); axR.grid(axis="y", alpha=0.3)

    fig.suptitle(f"{region}: projected SMC impact 2023-2027 (mean +/- 95% CI, {len(seeds)} seeds)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = f"data/projection_{region}_panel.png"; fig.savefig(out, dpi=130)
    print("saved", out)


if __name__ == "__main__":
    plot(sys.argv[1])
