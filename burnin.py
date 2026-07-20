"""
50-year burn-in for the Navrongo climate-driven model.

Adds realistic Ghana vital dynamics (births/deaths + young age structure) so a
genuine under-5 cohort exists, runs to transmission/immunity equilibrium, reports
under-5 PfPR each year, and serializes the final population state for reuse by the
intervention scenarios.

Smoke-test first:   python burnin.py 3     # short run to validate config
Full burn-in:       python burnin.py       # BURNIN_YEARS (50)
"""
import os
import sys
import json
import manifest

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask

import emodpy_malaria.malaria_config as malaria_config
import emodpy_malaria.demographics.MalariaDemographics as Demographics
from emodpy_malaria.reporters.builtin import add_malaria_summary_report
from emod_api.demographics.DemographicsTemplates import CrudeRate
import emod_api.config.default_from_schema_no_validation as dfs

# reuse climate + habitat setup from the baseline model
import ghana_model as G
import region_config as RC

BURNIN_YEARS = 50
CRUDE_BIRTH_RATE = 35            # per 1,000 per year (northern Ghana, high fertility)
POP = 2000                      # 2k baseline (fits RDT); severe-case power via replicate seeds
# Under-5 as the first age bin; remaining bins span older ages for context.
AGE_BINS = [5, 10, 15, 25, 50, 125]


def build_config_factory(sim_days):
    def build_config(config):
        config = malaria_config.set_team_defaults(config, manifest)
        malaria_config.add_species(config, manifest, [G.SPECIES])
        malaria_config.set_species_param(
            config, G.SPECIES, "Habitats",
            [G._habitat("TEMPORARY_RAINFALL", G.TEMP_RAINFALL_CAPACITY),
             G._habitat("CONSTANT", G.CONSTANT_CAPACITY)],
            overwrite=True,
        )
        # climate
        config.parameters.Climate_Model = "CLIMATE_BY_DATA"
        config.parameters.Climate_Update_Resolution = "CLIMATE_UPDATE_DAY"
        config.parameters.Enable_Climate_Stochasticity = 0
        for param, fname in G.WEATHER_FILES.items():
            setattr(config.parameters, param, fname)

        # vital dynamics: births + deaths + aging, complex age distribution from demog
        config.parameters.Enable_Vital_Dynamics = 1
        config.parameters.Enable_Birth = 1
        config.parameters.Enable_Aging = 1
        config.parameters.Enable_Natural_Mortality = 1
        config.parameters.Age_Initialization_Distribution_Type = "DISTRIBUTION_COMPLEX"
        config.parameters.Birth_Rate_Dependence = "FIXED_BIRTH_RATE"
        config.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_AGE_AND_GENDER"

        config.parameters.Simulation_Duration = sim_days
        config.parameters.Run_Number = 1
        config.parameters.x_Temporary_Larval_Habitat = G.DEFAULT_HABITAT_SCALE
        config.parameters.Enable_Default_Reporting = 1

        # serialize the final population state (end of burn-in)
        config.parameters.Serialization_Time_Steps = [sim_days]
        config.parameters.Serialized_Population_Writing_Type = "TIMESTEP"
        config.parameters.Serialization_Precision = "REDUCED"
        return config
    return build_config


def build_demographics(region="upper_east"):
    lat, lon = RC.coords(region)
    demog = Demographics.from_template_node(
        lat=lat, lon=lon, pop=POP, name=RC.REGIONS[region]["name"],
        forced_id=1, init_prev=0.1,
    )
    # sets fertility, mortality, and a consistent steady-state (young) age structure
    demog.SetEquilibriumVitalDynamics(CrudeRate(CRUDE_BIRTH_RATE))
    # persistent SMC-reach property (fixed reached/never-reached subsets)
    import effect_sizes as ES
    demog.AddIndividualPropertyAndHINT(
        Property="SMCReached", Values=["Y", "N"],
        InitialDistribution=[ES.SMC_REACHED_FRAC, 1 - ES.SMC_REACHED_FRAC])
    return demog


def build_task(sim_days, region="upper_east"):
    task = EMODTask.from_default2(
        config_path="config.json",
        eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file,
        param_custom_cb=build_config_factory(sim_days),
        campaign_builder=G.build_campaign,
        demog_builder=lambda: build_demographics(region),
        ep4_custom_cb=None,
    )
    wdir = RC.weather_dir(region)
    for f in sorted(os.listdir(wdir)):
        task.common_assets.add_asset(os.path.join(wdir, f))
    add_malaria_summary_report(
        task, manifest, start_day=0, end_day=sim_days,
        reporting_interval=365, age_bins=AGE_BINS,
    )
    return task


def main():
    region = "upper_east"
    args = [a for a in sys.argv[1:]]
    if args and args[0] in RC.REGIONS:
        region = args.pop(0)
    RC.check(region)
    years = int(args[0]) if args else BURNIN_YEARS
    sim_days = years * 365
    print(f"Running {years}-year burn-in for {region} ({sim_days} days), pop={POP}, CBR={CRUDE_BIRTH_RATE}/1000 ...")

    task = build_task(sim_days, region)
    experiment = Experiment.from_task(task, name=f"ghana_burnin_{region}_{years}yr")
    platform = Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB)
    experiment.run(platform=platform, wait_until_done=True)
    print("Status:", experiment.status, "| Succeeded:", experiment.succeeded)
    if not experiment.succeeded:
        raise SystemExit("Burn-in failed — see jobs/ logs.")

    exp_dir = os.path.join(manifest.job_directory, f"e_ghana_burnin_{region}_{years}yr_{experiment.id}")
    out = next(os.path.join(r) for r, _d, fs in os.walk(exp_dir)
               if "MalariaSummaryReport.json" in fs)
    sr = json.load(open(os.path.join(out, "MalariaSummaryReport.json")))
    u5 = [row[0] for row in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin"]]  # first bin = 0-5
    eir = sr["DataByTime"]["Annual EIR"]
    print("\nUnder-5 PfPR by year (last = equilibrium):", [round(x, 3) for x in u5[-6:]])
    print("Annual EIR by year (last):", round(eir[-2], 1))
    print("Serialized state written under:", out)


if __name__ == "__main__":
    main()
