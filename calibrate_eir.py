"""
Calibrate the seasonal model to a target annual EIR.

Sweeps `x_Temporary_Larval_Habitat` (the overall habitat/transmission scale)
across an experiment, reads each run's steady-state (final-year) Annual EIR from
its MalariaSummaryReport, then interpolates the scale that hits TARGET_EIR.

Produces:
  - console table of scale -> annual EIR
  - eir_calibration.png : EIR vs habitat scale (log-x) with the target marked

Run:  python calibrate_eir.py
"""
import os
import json
from functools import partial

import numpy as np

from idmtools.builders import SimulationBuilder
from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from emodpy.emod_task import EMODTask

import manifest
import seasonal_model

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


TARGET_EIR = 10.0
# Log-spaced habitat scales that should bracket the target (baseline x=1 -> EIR~26).
SCALES = [0.03, 0.1, 0.2, 0.35, 0.5, 1.0, 2.0, 5.0]
SWEEP_PARAM = "x_Temporary_Larval_Habitat"


def run_sweep():
    task = seasonal_model.build_task()
    builder = SimulationBuilder()
    builder.add_sweep_definition(
        partial(EMODTask.set_parameter_sweep_callback, param=SWEEP_PARAM),
        SCALES,
    )
    experiment = Experiment.from_builder(builder, base_task=task, name="eir_calibration")
    platform = Platform("Container", job_directory=manifest.job_directory)
    experiment.run(platform=platform, wait_until_done=True)
    if not experiment.succeeded:
        raise SystemExit("Calibration sweep failed — see jobs/ logs.")
    return experiment


def collect_results(experiment):
    """Return list of (scale, final_year_annual_EIR) by reading each sim's outputs."""
    exp_dir = os.path.join(manifest.job_directory, f"e_eir_calibration_{experiment.id}")
    rows = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        tags_path = os.path.join(entry.path, "tags.json")
        report_path = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(tags_path) and os.path.exists(report_path)):
            continue
        scale = float(json.load(open(tags_path))["tags"][SWEEP_PARAM])
        eir_by_year = json.load(open(report_path))["DataByTime"]["Annual EIR"]
        # Final full year = steady-state after burn-in. Last entry can be a partial year -> take year YEARS.
        final_eir = eir_by_year[seasonal_model.YEARS - 1]
        rows.append((scale, final_eir))
    rows.sort()
    return rows


def calibrate(rows):
    """Interpolate the habitat scale that yields TARGET_EIR (log-log interpolation)."""
    scales = np.array([r[0] for r in rows])
    eirs = np.array([r[1] for r in rows])
    # EIR rises monotonically with scale; interpolate in log-log space for a smooth
    # estimate. Drop zero-EIR runs (log undefined) before interpolating.
    pos = eirs > 0
    order = np.argsort(eirs[pos])
    log_scale_at_target = np.interp(
        np.log(TARGET_EIR), np.log(eirs[pos][order]), np.log(scales[pos][order])
    )
    return float(np.exp(log_scale_at_target)), scales, eirs


def plot(scales, eirs, best_scale, path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(scales, eirs, "o-", color="#1f77b4", label="simulated EIR")
    ax.axhline(TARGET_EIR, ls="--", color="#d62728", label=f"target EIR = {TARGET_EIR:g}")
    ax.axvline(best_scale, ls=":", color="#2ca02c",
               label=f"calibrated scale = {best_scale:.3g}")
    ax.set_xscale("log")
    ax.set_xlabel("x_Temporary_Larval_Habitat  (habitat / transmission scale)")
    ax.set_ylabel("Annual EIR (final year)")
    ax.set_title("Seasonal malaria model — EIR calibration")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("Saved plot:", path)


def main():
    experiment = run_sweep()
    rows = collect_results(experiment)

    print("\n  habitat scale ->  annual EIR (final year)")
    print("  " + "-" * 40)
    for scale, eir in rows:
        print(f"  {scale:>10.3g}   ->   {eir:8.2f}")

    best_scale, scales, eirs = calibrate(rows)
    print("\n  TARGET annual EIR:", TARGET_EIR)
    print(f"  Calibrated x_Temporary_Larval_Habitat = {best_scale:.4g}")

    plot(scales, eirs, best_scale, os.path.join(os.path.dirname(__file__), "eir_calibration.png"))


if __name__ == "__main__":
    main()
