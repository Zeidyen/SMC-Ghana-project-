"""
Paper-style seasonality verification (Diallo 2025 method):
run the calibrated-habitat model WITH vital dynamics, NO interventions, and compare
the model's monthly OVER-5 CLINICAL INCIDENCE to observed routine cases (both
rescaled to their own mean -> shape only). This removes the EIR-vs-cases lag and the
no-vital-dynamics immunity confound of the earlier quick check.

    python seasonality_verify.py <region>
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
from emodpy.emod_task import EMODTask

import emodpy_malaria.malaria_config as malaria_config
from emodpy_malaria.reporters.builtin import add_malaria_summary_report
import manifest
import ghana_model as G
import burnin
import region_config as RC

YEARS = 14
OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}
AGE_BINS = [5, 10, 15, 25, 50, 125]      # bin0 = under-5; bins>=1 = over-5


def build_config(config):
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
    config.parameters.x_Temporary_Larval_Habitat = 1.0
    config.parameters.Enable_Default_Reporting = 1
    return config


def run(region):
    RC.check(region)
    task = EMODTask.from_default2(
        config_path="config.json", eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file, param_custom_cb=build_config,
        campaign_builder=G.build_campaign,
        demog_builder=lambda: burnin.build_demographics(region), ep4_custom_cb=None)
    for f in sorted(os.listdir(RC.weather_dir(region))):
        task.common_assets.add_asset(os.path.join(RC.weather_dir(region), f))
    add_malaria_summary_report(task, manifest, start_day=0, end_day=YEARS * 365,
                               reporting_interval=30, age_bins=AGE_BINS, max_number_reports=200)
    exp = Experiment.from_task(task, name=f"ghana_seasver_{region}")
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("seasonality verify run failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_seasver_{region}_{exp.id}"))


def analyze(region, exp_dir):
    out = next(r for r, _d, fs in os.walk(exp_dir) if "MalariaSummaryReport.json" in fs)
    sr = json.load(open(os.path.join(out, "MalariaSummaryReport.json")))
    clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])  # [period, agebin]
    t = sr["DataByTime"]["Time Of Report"][:len(clin)]
    over5 = clin[:, 1:].sum(axis=1)                       # ages 5+
    dates = pd.to_datetime("2000-01-01") + pd.to_timedelta(t, unit="D")
    df = pd.DataFrame({"v": over5, "m": dates.month, "y": dates.year})
    df = df[df.y >= df.y.max() - 6]
    prof = df.groupby("m")["v"].mean(); prof = (prof / prof.mean()).reindex(range(1, 13))

    obs = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"])
    obs["m"] = obs.date.dt.month
    op = obs.groupby("m")[OBS_COL[region]].mean(); op = op / op.mean()

    corr = np.corrcoef(prof.values, op.values)[0, 1]
    print(f"\n{region}: model over-5 clinical-incidence seasonality vs observed cases")
    print(f"  model peak month = {int(prof.values.argmax())+1}, observed = {int(op.values.argmax())+1}")
    print(f"  shape correlation = {corr:.3f}")

    mlab = list("JFMAMJJASOND")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(range(1, 13), op.values, "o-", color="black", lw=2.5, label="observed cases")
    ax.plot(range(1, 13), prof.values, "s-", color="#d62728", lw=2, label="model over-5 clinical incidence")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(mlab); ax.axvline(10, ls=":", color="grey")
    ax.set_ylabel("relative to annual mean"); ax.legend()
    ax.set_title(f"{region}: seasonality (paper method) — corr={corr:.2f}")
    fig.tight_layout(); fig.savefig(f"data/seasver_{region}.png", dpi=130)
    print(f"  saved data/seasver_{region}.png")


if __name__ == "__main__":
    run(sys.argv[1])
