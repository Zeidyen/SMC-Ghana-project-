"""
Show option A (high x, RDT-matched) vs option B (low x, dynamics-matched):
RDT trajectory + pre-SMC seasonality + SMC-era seasonality, for two x values.

    python compare_ab.py <region> <xA> <xB>
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

OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}


def run(region, xA, xB):
    RC.check(region); H.SMC_ENABLED = True
    states = burnin_states(region)
    stage = os.path.join(manifest.job_directory, "_states"); os.makedirs(stage, exist_ok=True)
    tasks = []
    for x in [xA, xB]:
        xk = min(states, key=lambda k: abs(k - x))
        dest = os.path.join(stage, f"state_{region}_x{xk}.dtk")
        if not os.path.exists(dest):
            shutil.copy(states[xk], dest)
        tasks.append((xk, H.build_task(region, xk, dest)))
    exp = Experiment.from_task(tasks[0][1], name=f"ghana_ab_{region}")
    exp.simulations[0].tags["x"] = tasks[0][0]
    exp.simulations.append(Simulation.from_task(tasks[1][1], tags={"x": tasks[1][0]}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("A/B run failed")
    plot(region, os.path.join(manifest.job_directory, f"e_ghana_ab_{region}_{exp.id}"))


def series(sim_dir):
    sr = json.load(open(os.path.join(sim_dir, "output", "MalariaSummaryReport.json")))
    rdt = [r[0] for r in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"]]
    clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])[:, 0]
    n = min(len(rdt), len(clin)); tt = sr["DataByTime"]["Time Of Report"][:n]
    idx = pd.DatetimeIndex([pd.Timestamp(f"{H.SIM_START_YEAR}-01-01") + pd.Timedelta(days=v) for v in tt])
    return pd.Series(rdt[:n], index=idx), pd.Series(clin[:n], index=idx)


def monthly(mc, y0, y1):
    s = mc[(mc.index.year >= y0) & (mc.index.year <= y1)]
    p = s.groupby(s.index.month).mean(); return (p / p.mean()).reindex(range(1, 13)).values


def plot(region, exp_dir):
    d = pd.read_csv("data/three_region_data.csv", comment="#"); d = d[d.region == region]
    win = pd.read_csv("data/survey_windows.csv", comment="#")
    obs = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"]); obs["m"] = obs.date.dt.month; obs["y"] = obs.date.dt.year
    o15 = obs[obs.y == 2015].groupby("m")[OBS_COL[region]].mean(); o15 = (o15 / o15.mean()).reindex(range(1, 13)).values
    osmc = obs[(obs.y >= 2016)].groupby("m")[OBS_COL[region]].mean(); osmc = (osmc / osmc.mean()).reindex(range(1, 13)).values

    runs = {}
    for entry in os.scandir(exp_dir):
        if entry.is_dir() and entry.name != "Assets" and os.path.exists(os.path.join(entry.path, "tags.json")):
            x = float(json.load(open(os.path.join(entry.path, "tags.json")))["tags"]["x"])
            runs[x] = series(entry.path)
    xs = sorted(runs)
    colA, colB = "#8b0000", "#1f77b4"     # high-x deep red, low-x blue
    cols = {xs[-1]: colA, xs[0]: colB}
    mlab = list("JFMAMJJASOND")

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
    # RDT trajectory
    for x in xs:
        mr, _ = runs[x]
        ax[0].plot(mr.index, mr.values, color=cols[x], lw=1.2, label=f"x={x:g}")
    obs_dates = [pd.Timestamp(f"{int(r.year)}-01-01") + pd.Timedelta(days=int((win[win.year == r.year].iloc[0].doy_start + min(win[win.year == r.year].iloc[0].doy_end, 364)) / 2)) for _, r in d.iterrows()]
    ax[0].plot(obs_dates, d.pfpr_rdt, "o", color="black", ms=9, zorder=5, label="observed RDT")
    ax[0].set_ylim(0, 0.85); ax[0].set_title("RDT trajectory 2011-2022"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    # pre-SMC seasonality
    ax[1].plot(range(1, 13), o15, "o-", color="black", lw=2.5, label="observed 2015")
    for x in xs:
        _, mc = runs[x]; p = monthly(mc, 2011, 2015)
        ax[1].plot(range(1, 13), p, "s-", color=cols[x], label=f"x={x:g} (r={np.corrcoef(p,o15)[0,1]:.2f})")
    ax[1].set_xticks(range(1, 13)); ax[1].set_xticklabels(mlab); ax[1].axvline(10, ls=":", color="grey")
    ax[1].set_title("PRE-SMC seasonality (2015)"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    # SMC-era seasonality
    ax[2].plot(range(1, 13), osmc, "o-", color="black", lw=2.5, label="observed 2016-24")
    for x in xs:
        _, mc = runs[x]; p = monthly(mc, 2016, 2022)
        ax[2].plot(range(1, 13), p, "s-", color=cols[x], label=f"x={x:g} (r={np.corrcoef(p,osmc)[0,1]:.2f})")
    ax[2].set_xticks(range(1, 13)); ax[2].set_xticklabels(mlab); ax[2].axvline(10, ls=":", color="grey")
    ax[2].set_title("SMC-era seasonality (2016+)"); ax[2].legend(fontsize=8); ax[2].grid(alpha=0.3)
    fig.suptitle(f"{region}: A (high x={xs[-1]:g}, red) vs B (low x={xs[0]:g}, blue)")
    fig.tight_layout(); fig.savefig(f"data/compare_ab_{region}.png", dpi=130)
    print(f"saved data/compare_ab_{region}.png  (x={xs})")


if __name__ == "__main__":
    run(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
