"""
Joint PfPR-trajectory calibration for a region.

For each burn-in transmission scale x (from the region's burn-in sweep), run the
2008-2022 historical pickup with real interventions, sample modeled under-5
microscopy PfPR at each survey's field window, and score the fit vs observed.
Pick the x with the lowest RMSE. EIR is reported alongside as a secondary check
(never fed in). Produces a plot overlaying all candidate trajectories.

    python calibrate_trajectory.py <region>
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

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation

import manifest
import region_config as RC
import historical as H


def burnin_states(region):
    """Map x -> serialized burn-in state path, merged across ALL calibration sweeps
    for the region (newer sweep wins for a given x)."""
    exps = sorted(glob.glob(os.path.join(manifest.job_directory, f"e_ghana_calib_{region}_*")),
                  key=os.path.getmtime)                       # oldest first; newer overwrites
    states = {}
    for exp in exps:
        for entry in os.scandir(exp):
            if not entry.is_dir() or entry.name == "Assets":
                continue
            tags = os.path.join(entry.path, "tags.json")
            st = glob.glob(os.path.join(entry.path, "output", "state-*.dtk"))
            if os.path.exists(tags) and st:
                x = float(json.load(open(tags))["tags"]["x_Temporary_Larval_Habitat"])
                states[round(x, 3)] = st[0]
    if not states:
        raise SystemExit(f"no burn-in states for {region}; run calibrate_pfpr.py {region} first")
    return dict(sorted(states.items()))


def run(region):
    RC.check(region)
    states = burnin_states(region)
    print(f"{region}: running historical pickup at x = {list(states)}")

    # stage each burn-in state under a unique name so all x can share one experiment
    import shutil
    stage = os.path.join(manifest.job_directory, "_states")
    os.makedirs(stage, exist_ok=True)
    tasks = []
    for x, sp in states.items():
        dest = os.path.join(stage, f"state_{region}_x{x}.dtk")
        if not os.path.exists(dest):
            shutil.copy(sp, dest)
        tasks.append((x, H.build_task(region, x, dest)))
    exp = Experiment.from_task(tasks[0][1], name=f"ghana_caltraj_{region}")
    exp.simulations[0].tags["x"] = tasks[0][0]
    for x, task in tasks[1:]:
        exp.simulations.append(Simulation.from_task(task, tags={"x": x}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("trajectory calibration failed — see jobs/ logs.")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_caltraj_{region}_{exp.id}"))


def analyze(region, exp_dir):
    df = pd.read_csv("data/three_region_data.csv", comment="#")
    d = df[df.region == region]
    win = pd.read_csv("data/survey_windows.csv", comment="#")
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")

    fig, ax = plt.subplots(figsize=(11, 5))
    results = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        tags = os.path.join(entry.path, "tags.json")
        rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(tags) and os.path.exists(rep)):
            continue
        x = float(json.load(open(tags))["tags"]["x"])
        sr = json.load(open(rep))
        u5 = [row[0] for row in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"]]  # RDT
        t = sr["DataByTime"]["Time Of Report"][:len(u5)]
        eir = sr["DataByTime"]["Annual EIR"][:len(u5)]
        model = pd.Series(u5, index=pd.DatetimeIndex([base + pd.Timedelta(days=v) for v in t]))
        preds = []
        for _, r in d.iterrows():
            w = win[win.year == r.year].iloc[0]
            ds = pd.Timestamp(f"{int(r.year)}-01-01") + pd.Timedelta(days=int(w.doy_start))
            de = pd.Timestamp(f"{int(r.year)}-01-01") + pd.Timedelta(days=int(min(w.doy_end, 364)))
            preds.append(model[(model.index >= ds) & (model.index <= de)].mean())
        rmse = np.sqrt(np.nanmean((d.pfpr_rdt.values - np.array(preds)) ** 2))
        peak_eir = max(eir)
        results.append(dict(x=x, rmse=rmse, peak_eir=peak_eir))
        ax.plot(model.index, model.values, lw=0.9, alpha=0.8, label=f"x={x} (RMSE {rmse:.3f})")

    obs_dates = [pd.Timestamp(f"{int(r.year)}-01-01") +
                 pd.Timedelta(days=int((win[win.year == r.year].iloc[0].doy_start +
                                        min(win[win.year == r.year].iloc[0].doy_end, 364)) / 2))
                 for _, r in d.iterrows()]
    ax.plot(obs_dates, d.pfpr_rdt, "o", color="black", ms=9, zorder=5, label="observed (RDT)")
    ax.set_ylim(0, 0.8); ax.set_ylabel("Under-5 PfPR"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title(f"{region}: PfPR trajectory calibration over transmission scale")
    fig.tight_layout(); fig.savefig(f"data/caltraj_{region}.png", dpi=130)

    res = pd.DataFrame(results).sort_values("rmse")
    print(f"\n=== {region} trajectory fit by x ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    best = res.iloc[0]
    print(f"\nBEST: x={best.x} (RMSE {best.rmse:.3f}, peak EIR {best.peak_eir:.0f})")
    print(f"saved data/caltraj_{region}.png")


if __name__ == "__main__":
    run(sys.argv[1])
