"""
Minimal emodpy-malaria smoke test.

Builds a single-node MALARIA_SIM, runs it locally inside a Docker container
(via idmtools ContainerPlatform + OrbStack), and reports success/failure.

Run:  python run_sim.py
"""
import os
import manifest

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask

import emodpy_malaria.malaria_config as malaria_config
import emodpy_malaria.demographics.MalariaDemographics as Demographics


SIM_DURATION_DAYS = 90


def build_config(config):
    """Configure a minimal falciparum MALARIA_SIM with one vector species."""
    config = malaria_config.set_team_defaults(config, manifest)
    malaria_config.add_species(config, manifest, ["gambiae"])
    config.parameters.Simulation_Duration = SIM_DURATION_DAYS
    config.parameters.Run_Number = 1
    # Write the default InsetChart.json time-series report
    config.parameters.Enable_Default_Reporting = 1
    return config


def build_campaign():
    """No interventions — just let transmission run from the seeded prevalence."""
    import emod_api.campaign as campaign
    campaign.set_schema(manifest.schema_file)
    return campaign


def build_demographics():
    """Single 1,000-person node with 20% initial prevalence."""
    return Demographics.from_template_node(
        lat=0, lon=0, pop=1000, name="smoke_node", forced_id=1, init_prev=0.2
    )


def main():
    task = EMODTask.from_default2(
        config_path="config.json",
        eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file,
        param_custom_cb=build_config,
        campaign_builder=build_campaign,
        demog_builder=build_demographics,
        ep4_custom_cb=None,
    )
    print("Task built. Creating experiment...")

    experiment = Experiment.from_task(task, name="malaria_smoke_test")

    platform = Platform(
        "Container",
        job_directory=manifest.job_directory,
    )

    experiment.run(platform=platform, wait_until_done=True)

    print("Experiment status:", experiment.status)
    print("Succeeded:", experiment.succeeded)
    if not experiment.succeeded:
        raise SystemExit("Simulation did NOT succeed — check logs under jobs/.")
    print("Experiment id:", experiment.id)
    print("SUCCESS: malaria simulation ran to completion inside Docker.")


if __name__ == "__main__":
    main()
