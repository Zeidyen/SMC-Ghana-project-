"""
Intervention scenarios for the Navrongo RTS,S/R21 + SMC study.

Each scenario picks up the serialized 50-year equilibrium population, applies its
interventions, runs the intervention period, and reports under-5 clinical incidence
and PfPR. Cases-averted are computed vs the baseline arm.

    python scenarios.py run 6            # run all arms for 6 intervention years
    python scenarios.py run 6 baseline SMC   # subset of arms
    python scenarios.py analyze <experiment_dir>

The serialized state is auto-located from the newest 50-yr burn-in (x=1). Once the
model is calibrated, re-burn-in at the calibrated x and point STATE_FILE there.
"""
import os
import sys
import json
import glob

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from emodpy.emod_task import EMODTask

import emodpy_malaria.malaria_config as malaria_config
from emodpy_malaria.reporters.builtin import add_malaria_summary_report

import manifest
import ghana_model as G
import burnin
import interventions as I

# transmission scale of the burn-in we pick up from (x=1 until calibrated)
PICKUP_X = 1.0

# scenario name -> list of intervention adders (each: fn(campaign, n_years))
SCENARIOS = {
    "baseline": [],
    "SMC": [I.add_smc],
    "RTSS": [I.add_rtss],
    "R21": [I.add_r21],
    "SMC+RTSS": [I.add_smc, I.add_rtss],
    "SMC+R21": [I.add_smc, I.add_r21],
}


def find_state_file():
    exps = sorted(glob.glob(os.path.join(manifest.job_directory, "e_ghana_burnin_50yr_*")),
                  key=os.path.getmtime, reverse=True)
    for exp in exps:
        hits = glob.glob(os.path.join(exp, "*", "output", "state-*.dtk"))
        if hits:
            return hits[0]
    raise SystemExit("No serialized 50-yr burn-in state found — run burnin.py 50 first.")


def build_pickup_config(n_years, state_filename):
    def cfg(config):
        config = malaria_config.set_team_defaults(config, manifest)
        malaria_config.add_species(config, manifest, [G.SPECIES])
        malaria_config.set_species_param(
            config, G.SPECIES, "Habitats",
            [G._habitat("TEMPORARY_RAINFALL", G.TEMP_RAINFALL_CAPACITY),
             G._habitat("CONSTANT", G.CONSTANT_CAPACITY)],
            overwrite=True,
        )
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

        # pick up the burned-in population instead of re-running 50 years
        config.parameters.Serialized_Population_Reading_Type = "READ"
        config.parameters.Serialized_Population_Path = "Assets"
        config.parameters.Serialized_Population_Filenames = [state_filename]
        config.parameters.Enable_Random_Generator_From_Serialized_Population = 0

        config.parameters.Simulation_Duration = n_years * 365
        config.parameters.Run_Number = 1
        config.parameters.x_Temporary_Larval_Habitat = PICKUP_X
        config.parameters.Enable_Default_Reporting = 1
        return config
    return cfg


def build_campaign(scenario, n_years):
    def bc():
        import emod_api.campaign as campaign
        campaign.set_schema(manifest.schema_file)
        for adder in SCENARIOS[scenario]:
            adder(campaign, n_years)
        return campaign
    return bc


def build_pickup_task(scenario, n_years, state_path):
    state_filename = os.path.basename(state_path)
    task = EMODTask.from_default2(
        config_path="config.json",
        eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file,
        param_custom_cb=build_pickup_config(n_years, state_filename),
        campaign_builder=build_campaign(scenario, n_years),
        demog_builder=burnin.build_demographics,
        ep4_custom_cb=None,
    )
    for f in sorted(os.listdir(G.WEATHER_DIR)):
        task.common_assets.add_asset(os.path.join(G.WEATHER_DIR, f))
    task.common_assets.add_asset(state_path)          # the serialized .dtk
    add_malaria_summary_report(
        task, manifest, start_day=0, end_day=n_years * 365,
        reporting_interval=365, age_bins=burnin.AGE_BINS,
    )
    return task


def run(n_years, names):
    state_path = find_state_file()
    print("Picking up from:", state_path)
    print("Scenarios:", names, "| intervention years:", n_years)

    tasks = [build_pickup_task(s, n_years, state_path) for s in names]
    experiment = Experiment.from_task(tasks[0], name="ghana_scenarios")
    experiment.simulations[0].tags["scenario"] = names[0]
    for scen, task in zip(names[1:], tasks[1:]):
        sim = Simulation.from_task(task, tags={"scenario": scen})
        experiment.simulations.append(sim)

    platform = Platform("Container", job_directory=manifest.job_directory)
    experiment.run(platform=platform, wait_until_done=True)
    print("Status:", experiment.status, "| Succeeded:", experiment.succeeded)
    if not experiment.succeeded:
        raise SystemExit("Scenario run failed — see jobs/ logs.")
    exp_dir = os.path.join(manifest.job_directory, f"e_ghana_scenarios_{experiment.id}")
    analyze(exp_dir)


def analyze(exp_dir):
    """Under-5 annual clinical incidence + PfPR by scenario; cases averted vs baseline."""
    results = {}
    for entry in os.scandir(exp_dir):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        tags = os.path.join(entry.path, "tags.json")
        rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(tags) and os.path.exists(rep)):
            continue
        scen = json.load(open(tags))["tags"].get("scenario", entry.name[:8])
        sr = json.load(open(rep))
        clin = [row[0] for row in sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"]]
        pfpr = [row[0] for row in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin"]]
        # mean over full intervention period (drop the final partial report if present)
        n = min(len(clin), len(pfpr))
        results[scen] = dict(u5_clinical=sum(clin[:n]) / n, u5_pfpr=sum(pfpr[:n]) / n)

    base = results.get("baseline", {}).get("u5_clinical")
    print(f"\n{'scenario':12s} {'U5 clinical/yr':>16s} {'U5 PfPR':>10s} {'cases averted/1000':>20s} {'% reduction':>12s}")
    print("-" * 74)
    for scen in [s for s in SCENARIOS if s in results]:
        r = results[scen]
        if base:
            averted = (base - r["u5_clinical"]) * 1000
            pct = 100 * (base - r["u5_clinical"]) / base
            extra = f"{averted:>20.1f} {pct:>11.1f}%"
        else:
            extra = ""
        print(f"{scen:12s} {r['u5_clinical']:>16.3f} {r['u5_pfpr']:>10.3f} {extra}")
    return results


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        analyze(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "run":
        n_years = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        names = sys.argv[3:] if len(sys.argv) > 3 else list(SCENARIOS.keys())
        run(n_years, names)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
