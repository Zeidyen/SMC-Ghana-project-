"""
Step 2: with x fixed (Upper East ~1.79), calibrate the SMC EFFECT. Sweep effective
SMC coverage (independent per-cycle draws already), and for each check:
  - SMC-era under-5 seasonality vs observed 2016-24 (target: smooth Oct peak, NO rebound), and
  - SMC-era RDT reduction at 2016/2019/2022.
Goal: coverage that reproduces the observed modest, shape-preserving reduction.

    python calibrate_smc.py <region> <x>
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
import effect_sizes as ES
from calibrate_trajectory import burnin_states

COVERAGES = [0.30, 0.50, 0.70, 0.88]
OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}


def run(region, x):
    RC.check(region)
    H.SMC_ENABLED = True
    states = burnin_states(region)
    xk = min(states, key=lambda k: abs(k - x))
    stage = os.path.join(manifest.job_directory, "_states")
    os.makedirs(stage, exist_ok=True)
    dest = os.path.join(stage, f"state_{region}_x{xk}.dtk")
    if not os.path.exists(dest):
        shutil.copy(states[xk], dest)
    print(f"{region}: SMC coverage sweep at x={xk}")

    tasks = []
    for cov in COVERAGES:
        ES.SMC_COVERAGE = cov                    # captured when the campaign builds
        tasks.append((cov, H.build_task(region, xk, dest)))
    exp = Experiment.from_task(tasks[0][1], name=f"ghana_smc_{region}")
    exp.simulations[0].tags["cov"] = tasks[0][0]
    for cov, t in tasks[1:]:
        exp.simulations.append(Simulation.from_task(t, tags={"cov": cov}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("SMC sweep failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_smc_{region}_{exp.id}"))


def analyze(region, exp_dir):
    d = pd.read_csv("data/three_region_data.csv", comment="#"); d = d[d.region == region].set_index("year")
    win = pd.read_csv("data/survey_windows.csv", comment="#")
    obs = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"]); obs["m"] = obs.date.dt.month; obs["y"] = obs.date.dt.year
    o_smc = obs[(obs.y >= 2016) & (obs.y <= 2024)].groupby("m")[OBS_COL[region]].mean(); o_smc = (o_smc / o_smc.mean()).reindex(range(1, 13)).values
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")

    mlab = list("JFMAMJJASOND")
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    ax[0].plot(range(1, 13), o_smc, "o-", color="black", lw=2.5, label="observed 2016-24", zorder=5)
    rows = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        cov = float(json.load(open(t))["tags"]["cov"]); sr = json.load(open(rep))
        clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])[:, 0]
        rdt = [row[0] for row in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"]]
        n = min(len(clin), len(rdt)); tt = sr["DataByTime"]["Time Of Report"][:n]
        idx = pd.DatetimeIndex([base + pd.Timedelta(days=v) for v in tt])
        mc = pd.Series(clin[:n], index=idx); mr = pd.Series(rdt[:n], index=idx)
        s = mc[(mc.index.year >= 2016) & (mc.index.year <= 2022)]
        prof = s.groupby(s.index.month).mean(); prof = (prof / prof.mean()).reindex(range(1, 13)).values
        corr = np.corrcoef(prof, o_smc)[0, 1]
        rdts = {}
        for y in [2016, 2019, 2022]:
            w = win[win.year == y].iloc[0]
            ds = pd.Timestamp(f"{y}-01-01") + pd.Timedelta(days=int(w.doy_start))
            de = pd.Timestamp(f"{y}-01-01") + pd.Timedelta(days=int(min(w.doy_end, 364)))
            rdts[y] = mr[(mr.index >= ds) & (mr.index <= de)].mean()
        rows.append(dict(cov=cov, seas_corr=corr, peak=int(np.argmax(prof)) + 1,
                         rdt2016=rdts[2016], rdt2019=rdts[2019], rdt2022=rdts[2022]))
        ax[0].plot(range(1, 13), prof, "s-", ms=4, alpha=0.85, label=f"cov={cov} (r={corr:.2f})")
    ax[0].set_xticks(range(1, 13)); ax[0].set_xticklabels(mlab); ax[0].axvline(10, ls=":", color="grey")
    ax[0].set_title("SMC-era under-5 seasonality"); ax[0].set_ylabel("rel. to annual mean"); ax[0].legend(fontsize=8)
    res = pd.DataFrame(rows).sort_values("cov")
    ax[1].axis("off")
    ax[1].text(0.0, 0.9, f"observed RDT: 2016={d.loc[2016,'pfpr_rdt']:.2f} 2019={d.loc[2019,'pfpr_rdt']:.2f} 2022={d.loc[2022,'pfpr_rdt']:.2f}", fontsize=10)
    ax[1].text(0.0, 0.75, res.to_string(index=False, float_format=lambda v: f"{v:.3f}"), family="monospace", fontsize=9, va="top")
    fig.suptitle(f"{region}: SMC coverage calibration (fixed x)")
    fig.tight_layout(); fig.savefig(f"data/smc_calib_{region}.png", dpi=130)
    print(f"\n=== {region} SMC coverage sweep (observed SMC-era peak=Oct) ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("saved data/smc_calib_" + region + ".png")


if __name__ == "__main__":
    run(sys.argv[1], float(sys.argv[2]))
