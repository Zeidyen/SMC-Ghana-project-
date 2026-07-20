"""
Quick x (transmission) calibration at 20k: run baseline HISTORICAL pickups
(2008-2022, no projection) at several x_Temporary_Larval_Habitat values from the
existing 20k burn-in state, and compare 2016-2022 under-5 RDT (HRP2) to the
survey targets. Finds the x that reproduces the observed prevalence trajectory.

    python calib_x_20k.py run          # launch the sweep
    python calib_x_20k.py fit          # after it finishes: rank x by RDT fit
"""
import os
import sys
import glob
import json
import shutil

import numpy as np
import pandas as pd

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation

import manifest
import region_config as RC
import historical as H
from calibrate_trajectory import burnin_states

REGION = "upper_east"
X_VALUES = [1.789]                             # 2k validation: confirm the locked x reproduces RDT
SURVEY = {2016: 0.258, 2019: 0.306, 2022: 0.336}   # under-5 RDT targets (calibration window)
EXP_NAME = f"ghana_calibx_{REGION}"


def run():
    RC.check(REGION)
    H.SMC_ENABLED = True
    H.EXTRA_YEARS = 0          # historical only, 2008-2022 (fast: no projection years)
    H.SMC_SCENARIO = "baseline"
    states = burnin_states(REGION)
    xk = min(states, key=lambda k: abs(k - 1.789))
    stage = os.path.join(manifest.job_directory, "_states"); os.makedirs(stage, exist_ok=True)
    dest = os.path.join(stage, f"state_{REGION}_x{xk}.dtk")
    if not os.path.exists(dest) or os.path.getmtime(states[xk]) > os.path.getmtime(dest):
        shutil.copy(states[xk], dest)
    print(f"calibrating x at 20k from state x={xk}; testing {X_VALUES}")

    tasks = [(x, H.build_task(REGION, x, dest, run_number=1)) for x in X_VALUES]
    exp = Experiment.from_task(tasks[0][1], name=EXP_NAME)
    exp.simulations[0].tags.update({"xcal": tasks[0][0]})
    for x, t in tasks[1:]:
        exp.simulations.append(Simulation.from_task(t, tags={"xcal": x}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    print("done" if exp.succeeded else "FAILED", exp.id)


def fit():
    exp = sorted(glob.glob(os.path.join(manifest.job_directory, f"e_{EXP_NAME}_*")),
                 key=os.path.getmtime)[-1]
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    print(f"\n=== x calibration vs survey RDT (under-5, 2016-2022) ===")
    print(f"{'x':>6} " + " ".join(f"{y:>7}" for y in SURVEY) + f"{'mean|err|':>10}")
    print(f"{'survey':>6} " + " ".join(f"{SURVEY[y]:>7.3f}" for y in SURVEY))
    rows = []
    for entry in os.scandir(exp):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        x = float(json.load(open(t))["tags"]["xcal"]); sr = json.load(open(rep))
        rdt = np.array(sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"])[:, 0]
        tt = np.array(sr["DataByTime"]["Time Of Report"][:len(rdt)])
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        vals = {y: float(rdt[yr == y].mean()) for y in SURVEY}
        err = np.mean([abs(vals[y] - SURVEY[y]) for y in SURVEY])
        rows.append((x, vals, err))
    for x, vals, err in sorted(rows):
        print(f"{x:>6.1f} " + " ".join(f"{vals[y]:>7.3f}" for y in SURVEY) + f"{err:>10.3f}")
    best = min(rows, key=lambda r: r[2])
    print(f"\nbest x = {best[0]} (mean|err| = {best[2]:.3f})")


if __name__ == "__main__":
    (fit if len(sys.argv) > 1 and sys.argv[1] == "fit" else run)()
