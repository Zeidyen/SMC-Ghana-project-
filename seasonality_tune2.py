"""
Stage 1 (paper method): tune a climate-informed LINEAR_SPLINE monthly-habitat
profile to match the observed UNDER-5 case seasonality. The profile is built from
the rainfall climatology raised to a sharpness exponent gamma (higher = sharper wet
peak, lower dry-season floor). Runs with vital dynamics, no interventions, and
compares model under-5 clinical-incidence seasonality to observed under-5 cases.

    python seasonality_tune2.py <region>
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
from emodpy.emod_task import EMODTask

import emodpy_malaria.malaria_config as malaria_config
from emodpy_malaria.reporters.builtin import add_malaria_summary_report
import manifest
import ghana_model as G
import burnin
import region_config as RC

YEARS = 14
# Diagnostic: fixed calibrated habitat; sweep TRANSMISSION INTENSITY (x) to see how
# the under-5 clinical seasonality sharpens as transmission falls (seasonality-intensity
# coupling). Lower x -> less under-5 immunity -> sharper, later peak.
GAMMAS = [0.05, 0.1, 0.2, 0.5, 1.0]      # x values (tag kept as 'gamma')
OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}


def build_config(region, xval):
    def cfg(config):
        config = malaria_config.set_team_defaults(config, manifest)
        malaria_config.add_species(config, manifest, [G.SPECIES])
        malaria_config.set_species_param(
            config, G.SPECIES, "Habitats",
            [G._habitat("TEMPORARY_RAINFALL", G.TEMP_RAINFALL_CAPACITY),
             G._habitat("CONSTANT", G.CONSTANT_CAPACITY)], overwrite=True)
        config.parameters.Climate_Model = "CLIMATE_BY_DATA"
        config.parameters.Climate_Update_Resolution = "CLIMATE_UPDATE_DAY"
        config.parameters.Enable_Climate_Stochasticity = 0
        for p, f in G.WEATHER_FILES.items():
            setattr(config.parameters, p, f)
        config.parameters.Enable_Vital_Dynamics = 1
        config.parameters.Enable_Birth = 1
        config.parameters.Enable_Aging = 1
        config.parameters.Enable_Natural_Mortality = 1
        config.parameters.Age_Initialization_Distribution_Type = "DISTRIBUTION_COMPLEX"
        config.parameters.Birth_Rate_Dependence = "FIXED_BIRTH_RATE"
        config.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_AGE_AND_GENDER"
        config.parameters.Simulation_Duration = YEARS * 365
        config.parameters.Run_Number = 1
        config.parameters.x_Temporary_Larval_Habitat = xval
        config.parameters.Enable_Default_Reporting = 1
        return config
    return cfg


def build_task(region, gamma):
    task = EMODTask.from_default2(
        config_path="config.json", eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file, param_custom_cb=build_config(region, gamma),
        campaign_builder=G.build_campaign,
        demog_builder=lambda: burnin.build_demographics(region), ep4_custom_cb=None)
    for f in sorted(os.listdir(RC.weather_dir(region))):
        task.common_assets.add_asset(os.path.join(RC.weather_dir(region), f))
    add_malaria_summary_report(task, manifest, start_day=0, end_day=YEARS * 365,
                               reporting_interval=30, age_bins=[5, 10, 15, 25, 50, 125],
                               max_number_reports=200)
    return task


def run(region):
    RC.check(region)
    tasks = [(g, build_task(region, g)) for g in GAMMAS]
    exp = Experiment.from_task(tasks[0][1], name=f"ghana_seastune2_{region}")
    exp.simulations[0].tags["gamma"] = tasks[0][0]
    for g, t in tasks[1:]:
        exp.simulations.append(Simulation.from_task(t, tags={"gamma": g}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("spline sweep failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_seastune2_{region}_{exp.id}"))


def analyze(region, exp_dir):
    obs = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"]); obs["m"] = obs.date.dt.month
    op = obs.groupby("m")[OBS_COL[region]].mean(); op = (op / op.mean()).values
    mlab = list("JFMAMJJASOND")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(range(1, 13), op, "o-", color="black", lw=2.5, label="observed U5 cases", zorder=5)
    rows = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        g = json.load(open(t))["tags"]["gamma"]; sr = json.load(open(rep))
        clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])
        tt = sr["DataByTime"]["Time Of Report"][:len(clin)]
        u5 = clin[:, 0]; dates = pd.to_datetime("2000-01-01") + pd.to_timedelta(tt, unit="D")
        df = pd.DataFrame({"v": u5, "m": dates.month, "y": dates.year}); df = df[df.y >= df.y.max() - 6]
        prof = df.groupby("m")["v"].mean(); prof = (prof / prof.mean()).reindex(range(1, 13)).values
        corr = np.corrcoef(prof, op)[0, 1]; peak = int(np.argmax(prof)) + 1
        rows.append(dict(gamma=g, corr=corr, peak=peak))
        ax.plot(range(1, 13), prof, "s-", ms=4, alpha=0.85, label=f"gamma={g} (r={corr:.2f}, pk={peak})")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(mlab); ax.axvline(10, ls=":", color="grey")
    ax.set_ylabel("relative to annual mean"); ax.legend(fontsize=8)
    ax.set_title(f"{region}: LINEAR_SPLINE sharpness vs observed U5 (Oct peak)")
    fig.tight_layout(); fig.savefig(f"data/seastune2_{region}.png", dpi=130)
    res = pd.DataFrame(rows).sort_values("corr", ascending=False)
    print(f"\n=== {region} spline-sharpness seasonality (obs peak=10) ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"saved data/seastune2_{region}.png")


if __name__ == "__main__":
    run(sys.argv[1])
