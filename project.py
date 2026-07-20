"""
5-year projection (2023-2027) with replicate seeds -> % reduction in clinical
incidence vs the 4-cycle baseline, with 95% CIs. Scenarios: +5th cycle, age
extension to 10y and 15y, and combinations. Age bands: U5, 5-10, 10-15, U15.
Reductions are computed per-seed (baseline & scenario share pre-2023 trajectory),
then averaged.

    python project.py <region> <x>
"""
import os
import sys
import glob
import json
import shutil

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation

import manifest
import region_config as RC
import historical as H
from calibrate_trajectory import burnin_states

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"5cycle": "+5th cycle", "age10": "age to 10y", "age15": "age to 15y",
          "5cycle_age10": "5th + to 10y", "5cycle_age15": "5th + to 15y"}
SEEDS = list(range(1, 61))     # 60 replicate seeds at 2k -> severe-case statistical power
PROJ_YEARS = 5
BANDS = {"U5": [0], "5-10": [1], "10-15": [2], "U15": [0, 1, 2]}   # age-bin indices


def run(region, x):
    RC.check(region); H.SMC_ENABLED = True; H.EXTRA_YEARS = PROJ_YEARS
    states = burnin_states(region); xk = min(states, key=lambda k: abs(k - x))
    stage = os.path.join(manifest.job_directory, "_states"); os.makedirs(stage, exist_ok=True)
    dest = os.path.join(stage, f"state_{region}_x{xk}.dtk")
    # re-stage whenever the source burn-in is newer (or dest missing) so a fresh
    # burn-in (e.g. the 20k re-run) is never masked by a stale same-named copy
    if not os.path.exists(dest) or os.path.getmtime(states[xk]) > os.path.getmtime(dest):
        shutil.copy(states[xk], dest)
    print(f"{region}: projecting {len(SCENARIOS)} scenarios x {len(SEEDS)} seeds at x={xk}")
    print(f"  staged state <- {states[xk]}  ({os.path.getsize(dest)/1e6:.0f} MB)")

    tasks = []
    for scen in SCENARIOS:
        H.SMC_SCENARIO = scen
        for s in SEEDS:
            tasks.append((scen, s, H.build_task(region, xk, dest, run_number=s)))
    exp = Experiment.from_task(tasks[0][2], name=f"ghana_proj_{region}")
    exp.simulations[0].tags.update({"scen": tasks[0][0], "seed": tasks[0][1]})
    for scen, s, t in tasks[1:]:
        exp.simulations.append(Simulation.from_task(t, tags={"scen": scen, "seed": s}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("projection failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_proj_{region}_{exp.id}"))


def analyze(region, exp_dir):
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    # incid[scen][seed][band] = mean projected clinical incidence
    incid = {sc: {} for sc in SCENARIOS}
    for entry in os.scandir(exp_dir):
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
        incid[tg["scen"]][int(tg["seed"])] = {b: clin[proj][:, idx].sum(axis=1).mean() for b, idx in BANDS.items()}

    # per-seed % reduction vs baseline (paired by seed), then mean + 95% CI
    print(f"\n=== {region} projected % reduction in clinical incidence 2023-2027 (mean [95% CI], {len(SEEDS)} seeds) ===")
    print(f"{'scenario':14s} " + " ".join(f"{b:>16s}" for b in BANDS))
    summary = {}
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        row = {}
        cells = []
        for b in BANDS:
            red = [100 * (incid["baseline"][s][b] - incid[sc][s][b]) / incid["baseline"][s][b]
                   for s in SEEDS if s in incid[sc] and s in incid["baseline"]]
            m = np.mean(red); lo, hi = np.percentile(red, [2.5, 97.5])
            row[b] = (m, lo, hi); cells.append(f"{m:5.1f} [{lo:4.0f},{hi:4.0f}]")
        summary[sc] = row
        print(f"{LABELS[sc]:14s} " + " ".join(f"{c:>16s}" for c in cells))

    # plot: U5, 5-10, 10-15 % reduction with CI error bars, per scenario
    scen_p = [s for s in SCENARIOS if s != "baseline"]
    bands_plot = ["U5", "5-10", "10-15"]; colors = ["#d62728", "#1f77b4", "#2ca02c"]
    x = np.arange(len(scen_p)); w = 0.25
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, b in enumerate(bands_plot):
        m = [summary[s][b][0] for s in scen_p]
        lo = [summary[s][b][0] - summary[s][b][1] for s in scen_p]
        hi = [summary[s][b][2] - summary[s][b][0] for s in scen_p]
        ax.bar(x + (i - 1) * w, m, w, yerr=[lo, hi], capsize=3, color=colors[i], label=b)
    ax.set_xticks(x); ax.set_xticklabels([LABELS[s] for s in scen_p], fontsize=9)
    ax.set_ylabel("% reduction in clinical incidence vs baseline"); ax.legend(title="age band"); ax.grid(axis="y", alpha=0.3)
    ax.set_title(f"{region}: projected SMC impact 2023-2027 (mean +/- 95% CI, {len(SEEDS)} seeds)")
    fig.tight_layout(); fig.savefig(f"data/projection_{region}.png", dpi=130)
    print(f"\nsaved data/projection_{region}.png")


if __name__ == "__main__":
    run(sys.argv[1], float(sys.argv[2]))
