"""
Stage 1 calibration: tune the larval-habitat COMPOSITION to match observed
seasonality (before calibrating x for intensity).

Runs short climate-driven sims (fixed x, no interventions) for several habitat-type
mixes, extracts the monthly clinical-case seasonal profile, and scores each against
the observed routine-case seasonality. Habitat types swept: TEMPORARY_RAINFALL
(rainfall-tracking, sharp), WATER_VEGETATION (semi-permanent "backwash", extends
season), CONSTANT (year-round floor).

    python seasonality_tune.py <region>
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
import emodpy_malaria.demographics.MalariaDemographics as Demographics
import manifest
import ghana_model as G
import region_config as RC

POP = 1000
YEARS = 8            # enough for a stable seasonal cycle (use last 3 yrs)
FIX_X = 1.0
OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}

# Stage 1b: TEMPORARY_RAINFALL fixed (good Oct peak); sweep the CONSTANT permanent-
# habitat magnitude to lift the dry-season floor to match observed without moving the peak.
CANDIDATES = {
    "const_1e6": [("TEMPORARY_RAINFALL", 1e10), ("CONSTANT", 1e6)],   # current
    "const_1e8": [("TEMPORARY_RAINFALL", 1e10), ("CONSTANT", 1e8)],
    "const_3e8": [("TEMPORARY_RAINFALL", 1e10), ("CONSTANT", 3e8)],
    "const_7e8": [("TEMPORARY_RAINFALL", 1e10), ("CONSTANT", 7e8)],
    "const_1e9": [("TEMPORARY_RAINFALL", 1e10), ("CONSTANT", 1e9)],
}


def build_config(habitats):
    def cfg(config):
        config = malaria_config.set_team_defaults(config, manifest)
        malaria_config.add_species(config, manifest, [G.SPECIES])
        malaria_config.set_species_param(
            config, G.SPECIES, "Habitats",
            [G._habitat(t, c) for t, c in habitats], overwrite=True)
        config.parameters.Climate_Model = "CLIMATE_BY_DATA"
        config.parameters.Climate_Update_Resolution = "CLIMATE_UPDATE_DAY"
        config.parameters.Enable_Climate_Stochasticity = 0
        for p, f in G.WEATHER_FILES.items():
            setattr(config.parameters, p, f)
        config.parameters.Simulation_Duration = YEARS * 365
        config.parameters.Run_Number = 1
        config.parameters.x_Temporary_Larval_Habitat = FIX_X
        config.parameters.Enable_Default_Reporting = 1
        return config
    return cfg


def build_task(region, name, habitats):
    lat, lon = RC.coords(region)
    task = EMODTask.from_default2(
        config_path="config.json", eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file, param_custom_cb=build_config(habitats),
        campaign_builder=G.build_campaign,
        demog_builder=lambda: Demographics.from_template_node(
            lat=lat, lon=lon, pop=POP, name=region, forced_id=1, init_prev=0.2),
        ep4_custom_cb=None)
    for f in sorted(os.listdir(RC.weather_dir(region))):
        task.common_assets.add_asset(os.path.join(RC.weather_dir(region), f))
    return task


def run(region):
    RC.check(region)
    names = list(CANDIDATES)
    tasks = [build_task(region, n, CANDIDATES[n]) for n in names]
    exp = Experiment.from_task(tasks[0], name=f"ghana_seastune_{region}")
    exp.simulations[0].tags["hab"] = names[0]
    for n, t in zip(names[1:], tasks[1:]):
        exp.simulations.append(Simulation.from_task(t, tags={"hab": n}))
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    if not exp.succeeded:
        raise SystemExit("seasonality sweep failed")
    analyze(region, os.path.join(manifest.job_directory, f"e_ghana_seastune_{region}_{exp.id}"))


def obs_profile(region):
    df = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"])
    df["month"] = df.date.dt.month
    p = df.groupby("month")[OBS_COL[region]].mean()
    return (p / p.mean()).values


def analyze(region, exp_dir):
    obs = obs_profile(region)
    mlab = list("JFMAMJJASOND")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(range(1, 13), obs, "o-", color="black", lw=2.5, label="observed", zorder=5)
    rows = []
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        tags = os.path.join(entry.path, "tags.json")
        ic = os.path.join(entry.path, "output", "InsetChart.json")
        if not (os.path.exists(tags) and os.path.exists(ic)):
            continue
        name = json.load(open(tags))["tags"]["hab"]
        d = json.load(open(ic))
        ncc = np.array(d["Channels"]["New Clinical Cases"]["Data"])
        dates = pd.date_range("2000-01-01", periods=len(ncc), freq="D")
        s = pd.DataFrame({"ncc": ncc, "m": dates.month, "y": dates.year})
        s = s[s.y >= s.y.max() - 3]
        prof = s.groupby("m")["ncc"].sum()
        prof = (prof / prof.mean()).reindex(range(1, 13)).values
        corr = np.corrcoef(prof, obs)[0, 1]
        peak = int(np.argmax(prof)) + 1
        rows.append(dict(hab=name, corr=corr, peak_month=peak))
        ax.plot(range(1, 13), prof, "s-", ms=4, alpha=0.8, label=f"{name} (r={corr:.2f}, pk={peak})")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(mlab); ax.axvline(10, ls=":", color="grey")
    ax.set_ylabel("clinical cases / annual mean"); ax.legend(fontsize=8)
    ax.set_title(f"{region}: habitat-composition seasonality (obs peak = Oct)")
    fig.tight_layout(); fig.savefig(f"data/seastune_{region}.png", dpi=130)
    res = pd.DataFrame(rows).sort_values("corr", ascending=False)
    print(f"\n=== {region} seasonality by habitat mix (obs peak month = 10) ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"saved data/seastune_{region}.png")


if __name__ == "__main__":
    run(sys.argv[1])
