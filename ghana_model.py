"""
Climate-driven malaria model for Navrongo, northern Ghana.

Seasonality is generated mechanistically from real NASA POWER climate
(Climate_Model = CLIMATE_BY_DATA) acting on a rainfall-filled larval habitat
(TEMPORARY_RAINFALL), rather than a prescribed spline. The overall transmission
intensity is still tuned with `x_Temporary_Larval_Habitat`.

Prereqs (run once):
    python climate_fetch.py      # -> climate/navrongo_climatology.csv
    python build_weather.py      # -> climate/emod_weather/*.bin (+ .bin.json)

Run a baseline:
    python ghana_model.py
"""
import os
import json
import manifest

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask

import emodpy_malaria.malaria_config as malaria_config
import emodpy_malaria.demographics.MalariaDemographics as Demographics
from emodpy_malaria.reporters.builtin import add_malaria_summary_report
import emod_api.config.default_from_schema_no_validation as dfs


SPECIES = "gambiae"
POP = 1000
YEARS = 5                                   # <= weather span (6 yrs) built by build_weather.py
SIM_DURATION_DAYS = YEARS * 365
DEFAULT_HABITAT_SCALE = 1.0                 # x_Temporary_Larval_Habitat (calibration knob)

# Rainfall-driven habitat capacity + a small permanent refuge so transmission
# does not stochastically go extinct in the long dry season.
# Seasonality-calibrated (stage 1, Diallo 2025 method): TEMPORARY_RAINFALL gives the
# Oct peak; CONSTANT=1e7 best matches the observed UNDER-5 clinical-incidence
# seasonality (corr 0.75, Oct peak). LINEAR_SPLINE was worse (peaked Aug).
TEMP_RAINFALL_CAPACITY = 1e10
CONSTANT_CAPACITY = 1e7

WEATHER_DIR = os.path.join(os.path.dirname(__file__), "climate", "emod_weather")
WEATHER_FILES = {
    "Air_Temperature_Filename": "air_temperature.bin",
    "Land_Temperature_Filename": "land_temperature.bin",
    "Rainfall_Filename": "rainfall.bin",
    "Relative_Humidity_Filename": "relative_humidity.bin",
}


def _habitat(habitat_type, max_capacity):
    """Build a schema-valid VectorHabitat sub-node (mirrors configure_linear_spline)."""
    h = dfs.schema_to_config_subnode(manifest.schema_file, ["idmTypes", "idmType:VectorHabitat"])
    h.parameters.Habitat_Type = habitat_type
    h.parameters.Max_Larval_Capacity = max_capacity
    return h.parameters


def build_config(config):
    config = malaria_config.set_team_defaults(config, manifest)
    malaria_config.add_species(config, manifest, [SPECIES])

    # Replace the default LINEAR_SPLINE with a climate-responsive habitat set.
    malaria_config.set_species_param(
        config, SPECIES, "Habitats",
        [_habitat("TEMPORARY_RAINFALL", TEMP_RAINFALL_CAPACITY),
         _habitat("CONSTANT", CONSTANT_CAPACITY)],
        overwrite=True,
    )

    # Drive the model with real daily weather.
    config.parameters.Climate_Model = "CLIMATE_BY_DATA"
    config.parameters.Climate_Update_Resolution = "CLIMATE_UPDATE_DAY"
    config.parameters.Enable_Climate_Stochasticity = 0
    for param, fname in WEATHER_FILES.items():
        setattr(config.parameters, param, fname)

    config.parameters.Simulation_Duration = SIM_DURATION_DAYS
    config.parameters.Run_Number = 1
    config.parameters.x_Temporary_Larval_Habitat = DEFAULT_HABITAT_SCALE
    config.parameters.Enable_Default_Reporting = 1
    return config


def build_campaign():
    import emod_api.campaign as campaign
    campaign.set_schema(manifest.schema_file)
    return campaign


def build_demographics():
    return Demographics.from_template_node(
        lat=10.90, lon=-1.09, pop=POP, name="Navrongo", forced_id=1, init_prev=0.1
    )


def build_task():
    task = EMODTask.from_default2(
        config_path="config.json",
        eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file,
        param_custom_cb=build_config,
        campaign_builder=build_campaign,
        demog_builder=build_demographics,
        ep4_custom_cb=None,
    )
    # Ship the climate files alongside the Eradication binary / demographics.
    for f in sorted(os.listdir(WEATHER_DIR)):
        task.common_assets.add_asset(os.path.join(WEATHER_DIR, f))
    add_malaria_summary_report(
        task, manifest, start_day=0, end_day=SIM_DURATION_DAYS, reporting_interval=365
    )
    return task


def main():
    task = build_task()
    experiment = Experiment.from_task(task, name="ghana_navrongo_baseline")
    platform = Platform("Container", job_directory=manifest.job_directory)
    experiment.run(platform=platform, wait_until_done=True)
    print("Status:", experiment.status, "| Succeeded:", experiment.succeeded)
    if not experiment.succeeded:
        raise SystemExit("Climate-driven baseline failed — see jobs/ logs.")

    exp_dir = os.path.join(manifest.job_directory, f"e_ghana_navrongo_baseline_{experiment.id}")
    rep = next(os.path.join(r, f) for r, _d, fs in os.walk(exp_dir)
               for f in fs if f.startswith("MalariaSummaryReport"))
    eir = json.load(open(rep))["DataByTime"]["Annual EIR"]
    print("Annual EIR by year:", [round(e, 2) for e in eir])
    print("Experiment dir:", exp_dir)


if __name__ == "__main__":
    main()
