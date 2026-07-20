"""
Step 1 (no-SMC): calibrate transmission intensity x against the pre-SMC signal only,
so SMC doesn't confound it. For each x (SMC OFF in the model), score:
  - pre-SMC RDT prevalence at 2011 & 2014 (under-5 HRP2), and
  - the 2015 under-5 seasonality SHAPE vs observed 2015 cases.
Report both per x + a combined pick. RDT only.

    python calibrate_nosmc.py <region>
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

PRE_SMC_YEARS = [2011, 2014]
OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}


def run(region):
    RC.check(region)
    H.SMC_ENABLED = False                       # << no SMC for this calibration
    states = burnin_states(region)
    stage = os.path.join(manifest.job_directory, "_states")
    os.makedirs(stage, exist_ok=True)
    tasks = []
    for x, sp in states.items():
        dest = os.path.join(stage, f"state_{region}_x{x}.dtk")
        if not os.path.exists(dest):
            shutil.copy(sp, dest)
        tasks.append((x, H.build_task(region, x, dest)))
    print(f"{region}: no-SMC runs at x = {list(states)}")

    exp = Experiment.from_task(tasks[0][1], name=f"ghana_nosmc_{region}")
    exp.simulations[0].tags["x"] = tasks[0][0]
    for x, t in tasks[1:]:
        exp.simulations.append(Simulation.from_task(t, tags={"x": x}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("no-SMC calibration failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_nosmc_{region}_{exp.id}"))


def analyze(region, exp_dir):
    d = pd.read_csv("data/three_region_data.csv", comment="#"); d = d[d.region == region].set_index("year")
    win = pd.read_csv("data/survey_windows.csv", comment="#")
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    obs = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"]); obs["m"] = obs.date.dt.month; obs["y"] = obs.date.dt.year
    o2015 = obs[obs.y == 2015].groupby("m")[OBS_COL[region]].mean()
    o2015 = (o2015 / o2015.mean()).reindex(range(1, 13)).values

    rows = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        x = float(json.load(open(t))["tags"]["x"]); sr = json.load(open(rep))
        rdt = [row[0] for row in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"]]
        clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])[:, 0]
        tt = sr["DataByTime"]["Time Of Report"][:len(rdt)]
        idx = pd.DatetimeIndex([base + pd.Timedelta(days=v) for v in tt])
        mr = pd.Series(rdt, index=idx); mc = pd.Series(clin[:len(rdt)], index=idx)
        # pre-SMC RDT at 2011, 2014 (survey-window mean)
        preds = []
        for y in PRE_SMC_YEARS:
            w = win[win.year == y].iloc[0]
            ds = pd.Timestamp(f"{y}-01-01") + pd.Timedelta(days=int(w.doy_start))
            de = pd.Timestamp(f"{y}-01-01") + pd.Timedelta(days=int(min(w.doy_end, 364)))
            preds.append(mr[(mr.index >= ds) & (mr.index <= de)].mean())
        prev_rmse = np.sqrt(np.mean([(d.loc[y, "pfpr_rdt"] - p) ** 2 for y, p in zip(PRE_SMC_YEARS, preds)]))
        # 2015 seasonality shape (pre-SMC clinical incidence)
        s = mc[(mc.index.year >= 2011) & (mc.index.year <= 2015)]
        prof = s.groupby(s.index.month).mean(); prof = (prof / prof.mean()).reindex(range(1, 13)).values
        seas_corr = np.corrcoef(prof, o2015)[0, 1]
        rows.append(dict(x=x, prev_rmse=prev_rmse, seas_corr=seas_corr,
                         rdt2011=preds[0], rdt2014=preds[1], peak=int(np.argmax(prof)) + 1))
    res = pd.DataFrame(rows).sort_values("x")
    # combined score: normalize prev_rmse (lower better) and seas_corr (higher better)
    res["score"] = (res.prev_rmse / res.prev_rmse.max()) + (1 - res.seas_corr)
    res = res.sort_values("score")
    print(f"\n=== {region} NO-SMC calibration (obs: RDT 2011={d.loc[2011,'pfpr_rdt']:.2f}, 2014={d.loc[2014,'pfpr_rdt']:.2f}; 2015 peak=Oct) ===")
    print(res[["x", "rdt2011", "rdt2014", "prev_rmse", "seas_corr", "peak", "score"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nBEST (combined): x = {res.iloc[0].x}")
    res.to_csv(f"data/nosmc_fit_{region}.csv", index=False)


if __name__ == "__main__":
    run(sys.argv[1])
