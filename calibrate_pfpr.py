"""
Calibrate transmission (x_Temporary_Larval_Habitat) to a target UNDER-5 PfPR.

Strategy: sweep the habitat/transmission scale across full 50-year burn-ins,
read each run's EQUILIBRIUM under-5 PfPR (mean of the last EQUILIB_YEARS annual
reports), and build the x -> under-5 PfPR response curve. Any target PfPR is then
a lookup/interpolation on that curve.

    python calibrate_pfpr.py run       # launch the sweep (long: 50-yr burn-ins)
    python calibrate_pfpr.py fit 0.40  # after run completes: interpolate x for target=0.40
"""
import os
import sys
import json
import glob
from functools import partial

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from idmtools.builders import SimulationBuilder
from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from emodpy.emod_task import EMODTask

import manifest
import burnin
import region_config as RC

BURNIN_YEARS = 50
# Single burn-in at the calibrated x, now with the SMCReached IP demographics.
# dense larval-habitat sweep (up to 20, matching Upper East) for UW/Northern.
# The earlier [0.5,1,1.5,2,2.5,4] states merge in via burnin_states (newer wins).
SCALES = [0.1, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.0, 3.5, 5.0, 8.0, 12.0, 20.0]
PARAM = "x_Temporary_Larval_Habitat"
EQUILIB_YEARS = 5                                # average final N annual reports


def curve_csv(region):
    return os.path.join(os.path.dirname(__file__), f"calibration_curve_{region}.csv")


def run_sweep(region):
    RC.check(region)
    task = burnin.build_task(BURNIN_YEARS * 365, region)
    b = SimulationBuilder()
    b.add_sweep_definition(partial(EMODTask.set_parameter_sweep_callback, param=PARAM), SCALES)
    exp = Experiment.from_builder(b, base_task=task, name=f"ghana_calib_{region}")
    platform = Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB)
    exp.run(platform=platform, wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("Calibration sweep failed — see jobs/ logs.")
    rows = collect(exp, region)
    pd.DataFrame(rows, columns=["x", "u5_pfpr"]).to_csv(curve_csv(region), index=False)
    print(f"\nSaved natural-equilibrium curve ({region}) ->", curve_csv(region))
    print(pd.DataFrame(rows, columns=["x", "u5_pfpr"]).to_string(index=False,
          float_format=lambda v: f"{v:.4f}"))
    return rows


def collect(exp, region):
    exp_dir = os.path.join(manifest.job_directory, f"e_ghana_calib_{region}_{exp.id}")
    rows = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        tags = os.path.join(entry.path, "tags.json")
        rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(tags) and os.path.exists(rep)):
            continue
        x = float(json.load(open(tags))["tags"][PARAM])
        u5 = [row[0] for row in json.load(open(rep))["DataByTimeAndAgeBins"]["PfPR by Age Bin"]]
        rows.append((x, float(np.mean(u5[-EQUILIB_YEARS:]))))
    rows.sort()
    return rows


def fit(region, target):
    df = pd.read_csv(curve_csv(region)).sort_values("u5_pfpr")
    x = df["x"].values
    p = df["u5_pfpr"].values
    if not (p.min() <= target <= p.max()):
        print(f"WARNING: target {target} is outside the swept range [{p.min():.3f}, {p.max():.3f}] — extend SCALES.")
    x_star = float(np.exp(np.interp(target, p, np.log(x))))    # log-x interpolation
    print(f"\nTarget under-5 PfPR = {target}")
    print(f"Calibrated x_Temporary_Larval_Habitat = {x_star:.4g}")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(df.sort_values("x")["x"], df.sort_values("x")["u5_pfpr"], "o-", color="#1f77b4", label="model")
    ax.axhline(target, ls="--", color="#d62728", label=f"target = {target:g}")
    ax.axvline(x_star, ls=":", color="#2ca02c", label=f"calibrated x = {x_star:.3g}")
    ax.set_xscale("log")
    ax.set_xlabel("x_Temporary_Larval_Habitat"); ax.set_ylabel("Equilibrium under-5 PfPR")
    ax.set_title("Under-5 PfPR calibration (50-yr burn-in)"); ax.legend(); ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "calibration_pfpr.png")
    fig.savefig(out, dpi=130); print("Saved plot:", out)
    return x_star


def main():
    args = sys.argv[1:]
    if args and args[0] == "fit":
        fit(args[1], float(args[2]))            # fit <region> <target>
    elif args:
        run_sweep(args[0])                      # <region>
    else:
        print("usage: python calibrate_pfpr.py <region> | fit <region> <target>")


if __name__ == "__main__":
    main()
