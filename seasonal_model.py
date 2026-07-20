"""
Seasonal single-site malaria model (reusable builders).

Transmission seasonality is driven by a LINEAR_SPLINE larval habitat whose
capacity follows a Sahel-like single-rainy-season profile (peak ~August).
The overall transmission intensity is scaled by the config parameter
`x_Temporary_Larval_Habitat`, which is the knob we calibrate against EIR.

Run directly for a single baseline simulation that prints the annual EIR:
    python seasonal_model.py
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


# ---- model settings ---------------------------------------------------------
SPECIES = "gambiae"
POP = 1000
YEARS = 3
SIM_DURATION_DAYS = YEARS * 365
BASE_MAX_LARVAL_CAPACITY = 1e8          # peak habitat capacity (scaled by x_Temporary_Larval_Habitat)
DEFAULT_HABITAT_SCALE = 1.0             # x_Temporary_Larval_Habitat; the sweep overrides this per-sim

# Sahel-like monthly larval-capacity multipliers (Jan..Dec), normalized so the
# August peak == 1.0. Dry season is near-zero; rains build Jun-Aug, taper by Nov.
_MONTHLY = [0.017, 0.017, 0.017, 0.033, 0.067, 0.167,
            0.333, 1.000, 0.667, 0.267, 0.067, 0.033]
# Month-start day-of-year (0..334) plus a closing point at 365 that repeats Jan.
_MONTH_START_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]
SEASONAL_SPLINE = {
    "Times":  _MONTH_START_DAYS,
    "Values": _MONTHLY + [_MONTHLY[0]],
}


def build_config(config):
    """Falciparum MALARIA_SIM, one vector species with a seasonal spline habitat."""
    config = malaria_config.set_team_defaults(config, manifest)
    malaria_config.add_species(config, manifest, [SPECIES])

    spline_habitat = malaria_config.configure_linear_spline(
        manifest,
        max_larval_capacity=BASE_MAX_LARVAL_CAPACITY,
        capacity_distribution_number_of_years=1,      # pattern repeats every year
        capacity_distribution_over_time=SEASONAL_SPLINE,
    )
    malaria_config.set_species_param(config, SPECIES, "Habitats", [spline_habitat], overwrite=True)

    config.parameters.Simulation_Duration = SIM_DURATION_DAYS
    config.parameters.Run_Number = 1
    config.parameters.x_Temporary_Larval_Habitat = DEFAULT_HABITAT_SCALE
    config.parameters.Enable_Default_Reporting = 1
    return config


def build_campaign():
    """No interventions in the baseline seasonal model."""
    import emod_api.campaign as campaign
    campaign.set_schema(manifest.schema_file)
    return campaign


def build_demographics():
    """Single node; seed a little infection so transmission can establish."""
    return Demographics.from_template_node(
        lat=12.0, lon=-1.5, pop=POP, name="sahel_node", forced_id=1, init_prev=0.1
    )


def build_task():
    """Assemble the EMODTask and attach an annual MalariaSummaryReport (gives Annual EIR)."""
    task = EMODTask.from_default2(
        config_path="config.json",
        eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file,
        param_custom_cb=build_config,
        campaign_builder=build_campaign,
        demog_builder=build_demographics,
        ep4_custom_cb=None,
    )
    # One report per 365-day year -> YEARS annual summaries, each with an "Annual EIR".
    add_malaria_summary_report(
        task, manifest, start_day=0, end_day=SIM_DURATION_DAYS, reporting_interval=365
    )
    return task


def main():
    task = build_task()
    experiment = Experiment.from_task(task, name="seasonal_baseline")
    platform = Platform("Container", job_directory=manifest.job_directory)
    experiment.run(platform=platform, wait_until_done=True)
    print("Status:", experiment.status, "| Succeeded:", experiment.succeeded)
    if not experiment.succeeded:
        raise SystemExit("Baseline seasonal run failed — see jobs/ logs.")

    # Locate the single simulation's output and print annual EIR from the summary report.
    exp_dir = os.path.join(manifest.job_directory, f"e_seasonal_baseline_{experiment.id}")
    summary = None
    for root, _dirs, files in os.walk(exp_dir):
        for f in files:
            if f.startswith("MalariaSummaryReport") and f.endswith(".json"):
                summary = os.path.join(root, f)
    if not summary:
        raise SystemExit("No MalariaSummaryReport found.")
    data = json.load(open(summary))
    eir = data["DataByTime"]["Annual EIR"]
    print("Summary report:", summary)
    print("Annual EIR by year:", [round(e, 2) for e in eir])


if __name__ == "__main__":
    main()
