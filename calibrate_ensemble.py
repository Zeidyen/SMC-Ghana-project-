"""
Ensemble intensity calibration (Diallo 2025 style): run several transmission
scales x, each with multiple stochastic seeds, average the survey-window RDT
trajectory, and report the calibrated x as a mean with a confidence band. Fits
the full 2011-2022 observed RDT under-5 prevalence.

    python calibrate_ensemble.py <region>
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

X_GRID = [0.75, 1.0, 1.5, 2.5]
SEEDS = [1, 2, 3, 4, 5]


def run(region):
    RC.check(region)
    states = {x: sp for x, sp in burnin_states(region).items() if x in X_GRID}
    stage = os.path.join(manifest.job_directory, "_states")
    os.makedirs(stage, exist_ok=True)
    tasks = []
    for x, sp in states.items():
        dest = os.path.join(stage, f"state_{region}_x{x}.dtk")
        if not os.path.exists(dest):
            shutil.copy(sp, dest)
        for s in SEEDS:
            tasks.append((x, s, H.build_task(region, x, dest, run_number=s)))
    print(f"{region}: {len(tasks)} runs ({len(states)} x-values x {len(SEEDS)} seeds)")

    exp = Experiment.from_task(tasks[0][2], name=f"ghana_ens_{region}")
    exp.simulations[0].tags.update({"x": tasks[0][0], "seed": tasks[0][1]})
    for x, s, t in tasks[1:]:
        exp.simulations.append(Simulation.from_task(t, tags={"x": x, "seed": s}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("ensemble failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_ens_{region}_{exp.id}"))


def analyze(region, exp_dir):
    d = pd.read_csv("data/three_region_data.csv", comment="#"); d = d[d.region == region]
    win = pd.read_csv("data/survey_windows.csv", comment="#")
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    years = d.year.astype(int).tolist()

    recs = []  # (x, seed, year, model)
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; x, seed = float(tg["x"]), int(tg["seed"])
        sr = json.load(open(rep)); u5 = [row[0] for row in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"]]
        tt = sr["DataByTime"]["Time Of Report"][:len(u5)]
        m = pd.Series(u5, index=pd.DatetimeIndex([base + pd.Timedelta(days=v) for v in tt]))
        for _, r in d.iterrows():
            w = win[win.year == r.year].iloc[0]
            ds = pd.Timestamp(f"{int(r.year)}-01-01") + pd.Timedelta(days=int(w.doy_start))
            de = pd.Timestamp(f"{int(r.year)}-01-01") + pd.Timedelta(days=int(min(w.doy_end, 364)))
            recs.append((x, seed, int(r.year), m[(m.index >= ds) & (m.index <= de)].mean()))
    df = pd.DataFrame(recs, columns=["x", "seed", "year", "model"])
    obs = {int(r.year): r.pfpr_rdt for _, r in d.iterrows()}

    # per-x mean trajectory + RMSE of the seed-mean
    summary = []
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(years, [obs[y] for y in years], "o-", color="black", lw=2.5, ms=9, label="observed RDT", zorder=5)
    for x in sorted(df.x.unique()):
        g = df[df.x == x].groupby("year")["model"]
        mean, sd = g.mean(), g.std()
        rmse = np.sqrt(np.mean([(obs[y] - mean[y]) ** 2 for y in years]))
        summary.append(dict(x=x, rmse=rmse))
        ax.plot(years, [mean[y] for y in years], "s-", alpha=0.85, label=f"x={x} (RMSE {rmse:.3f})")
        ax.fill_between(years, [mean[y] - sd[y] for y in years], [mean[y] + sd[y] for y in years], alpha=0.15)
    ax.set_ylim(0, 0.8); ax.set_ylabel("under-5 RDT prevalence"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title(f"{region}: ensemble RDT calibration (mean +/- SD over {len(SEEDS)} seeds)")
    fig.tight_layout(); fig.savefig(f"data/ensemble_{region}.png", dpi=130)

    res = pd.DataFrame(summary).sort_values("rmse")
    print(f"\n=== {region} ensemble fit (full 2011-2022 RDT) ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"BEST x = {res.iloc[0].x}  (RMSE {res.iloc[0].rmse:.3f})")
    print(f"saved data/ensemble_{region}.png")


if __name__ == "__main__":
    run(sys.argv[1])
