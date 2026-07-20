"""
2-D exploration (user idea): vary habitat COMPOSITION (seasonality shape) x
transmission scale x (intensity) and check, for each combo:
  - under-5 clinical seasonality correlation vs observed 2015 shape, and
  - the natural-equilibrium under-5 RDT level (does it reach the observed ~0.65-0.77?)
Short vital-dynamics runs, NO interventions. Tests whether a sharper habitat can keep
the Oct under-5 peak at the high x that RDT prevalence requires.

    python calibrate_2d.py <region>
"""
import os
import sys
import glob
import json

import numpy as np
import pandas as pd

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

YEARS = 16
# habitat composition variants (sharpness: less CONSTANT -> sharper dry-season)
HABITATS = {
    "sharp(no const)": [("TEMPORARY_RAINFALL", 1e10)],
    "const1e6":        [("TEMPORARY_RAINFALL", 1e10), ("CONSTANT", 1e6)],
    "const1e7":        [("TEMPORARY_RAINFALL", 1e10), ("CONSTANT", 1e7)],
}
XVALS = [1.5, 2.0, 2.5]     # around the RDT-calibrated x~1.8
OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}


def build_config(habitats, x):
    def cfg(config):
        config = malaria_config.set_team_defaults(config, manifest)
        malaria_config.add_species(config, manifest, [G.SPECIES])
        malaria_config.set_species_param(config, G.SPECIES, "Habitats",
                                         [G._habitat(t, c) for t, c in habitats], overwrite=True)
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
        config.parameters.x_Temporary_Larval_Habitat = x
        config.parameters.Enable_Default_Reporting = 1
        return config
    return cfg


def build_task(region, habitats, x):
    task = EMODTask.from_default2(
        config_path="config.json", eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file, param_custom_cb=build_config(habitats, x),
        campaign_builder=G.build_campaign,
        demog_builder=lambda: burnin.build_demographics(region), ep4_custom_cb=None)
    for f in sorted(os.listdir(RC.weather_dir(region))):
        task.common_assets.add_asset(os.path.join(RC.weather_dir(region), f))
    add_malaria_summary_report(task, manifest, start_day=0, end_day=YEARS * 365,
                               reporting_interval=30, age_bins=[5, 10, 15, 25, 50, 125],
                               add_hrp2_prevalence=True, hrp2_detection_threshold=5, max_number_reports=220)
    return task


def run(region):
    RC.check(region)
    combos = [(h, x) for h in HABITATS for x in XVALS]
    tasks = [(h, x, build_task(region, HABITATS[h], x)) for h, x in combos]
    exp = Experiment.from_task(tasks[0][2], name=f"ghana_2d_{region}")
    exp.simulations[0].tags.update({"hab": tasks[0][0], "x": tasks[0][1]})
    for h, x, t in tasks[1:]:
        exp.simulations.append(Simulation.from_task(t, tags={"hab": h, "x": x}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("2d sweep failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_2d_{region}_{exp.id}"))


def analyze(region, exp_dir):
    obs = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"]); obs["m"] = obs.date.dt.month; obs["y"] = obs.date.dt.year
    o2015 = obs[obs.y == 2015].groupby("m")[OBS_COL[region]].mean(); o2015 = (o2015 / o2015.mean()).reindex(range(1, 13)).values
    rows = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; sr = json.load(open(rep))
        clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])[:, 0]
        rdt = np.array([r[0] for r in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"]])
        n = min(len(clin), len(rdt)); tt = sr["DataByTime"]["Time Of Report"][:n]
        yr = (pd.to_datetime("2000-01-01") + pd.to_timedelta(tt, unit="D"))
        mo = yr.month; keep = yr.year >= yr.year.max() - 6
        prof = pd.Series(clin[:n][keep]).groupby(mo[keep]).mean(); prof = (prof / prof.mean()).reindex(range(1, 13)).values
        rows.append(dict(hab=tg["hab"], x=float(tg["x"]),
                         seas_corr=np.corrcoef(prof, o2015)[0, 1], peak=int(np.argmax(prof)) + 1,
                         nat_rdt=float(np.mean(rdt[-24:]))))
    res = pd.DataFrame(rows).sort_values(["hab", "x"])
    print(f"\n=== {region} 2-D: habitat composition x intensity (obs 2015 peak=Oct; obs RDT 2011~0.77) ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    run(sys.argv[1])
