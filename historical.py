"""
Historical intervention layer (2008-2022) for a region.

Picks up the burn-in (natural equilibrium) population and runs the real-world
intervention scale-up: ITN, case management, SMC (from each region's start year),
and IRS (region-specific timeline). Coverages come from data/three_region_data.csv,
forward-filled between DHS/GMIS survey years. A 3-year run-in (2008-2010, held at
2011 coverage) lets interventions equilibrate before the first survey point.

Reports monthly under-5 microscopy PfPR so we can compare to survey PfPR at the
exact field months.

    python historical.py <region> <x> [state_path]
"""
import os
import sys
import json

import pandas as pd

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask

import emodpy_malaria.malaria_config as malaria_config
from emodpy_malaria.reporters.builtin import add_malaria_summary_report
from emodpy_malaria.interventions.usage_dependent_bednet import add_scheduled_usage_dependent_bednet
from emodpy_malaria.interventions.treatment_seeking import add_treatment_seeking
from emodpy_malaria.interventions.irs import add_scheduled_irs_housing_modification
from emodpy_malaria.interventions.drug_campaign import add_drug_campaign
from emodpy_malaria.interventions.outbreak import add_outbreak_individual

import manifest
import ghana_model as G
import burnin
import region_config as RC
import effect_sizes as ES

# ---- calendar --------------------------------------------------------------
SIM_START_YEAR = 2008           # 3-yr run-in before the 2011 survey
END_YEAR = 2022                 # end of the historical/calibration period
EXTRA_YEARS = 0                 # projection years beyond 2022 (set to 5 for predictions)
SMC_SCENARIO = "baseline"       # applies to years > 2022
SCENARIO = {
    "baseline":       dict(cycles=4, age_max=5.0),    # current policy: 4 cycles Jun-Sep, 3-59mo
    "5cycle":         dict(cycles=5, age_max=5.0),     # add an October cycle
    "age10":          dict(cycles=4, age_max=10.0),    # extend eligibility to 10y
    "age15":          dict(cycles=4, age_max=15.0),    # extend eligibility to 15y
    "5cycle_age10":   dict(cycles=5, age_max=10.0),    # 5th cycle + to 10y
    "5cycle_age15":   dict(cycles=5, age_max=15.0),    # 5th cycle + to 15y
}


def proj_end():
    return END_YEAR + EXTRA_YEARS


def n_years():
    return proj_end() - SIM_START_YEAR + 1

# ---- intervention timing (day-of-year) -------------------------------------
ITN_DOY = 121                   # ~1 May: mass ITN campaign before the season
# Ghana national LLIN mass-distribution years (~every 3 yr); 2006/2009 seed the run-in.
ITN_CAMPAIGN_YEARS = [2006, 2009, 2012, 2015, 2018, 2021, 2024, 2027]  # 3-yearly; continues through projection
IRS_DOY = 121                   # ~1 May, before transmission season
SMC_FIRST_DOY = 152             # ~1 June; 4 monthly cycles -> Jun/Jul/Aug/Sep
SMC_CYCLES, SMC_INTERVAL = 4, 30

# Importation (population connectivity): a modest steady inflow of infections so a
# single node cannot unrealistically eliminate under strong control. TUNABLE.
# MUST scale with population to keep the per-capita seeding constant: the RDT
# calibration was tuned at pop 2000 with 2 imports/cycle, so use POP/1000
# (=> 20/cycle at the 20k projection population). A fixed count silently breaks the
# fit when the population is scaled up (transmission drifts to elimination).
import burnin as _bn
IMPORT_PER_CYCLE = max(2, round(_bn.POP / 1000))   # 2 @ pop2000, 20 @ pop20000
IMPORT_INTERVAL = 30           # days between importation cycles
SMC_AGE_MIN, SMC_AGE_MAX = 0.25, 5.0

# Effect sizes are literature-sourced in effect_sizes.py (ES).
SMC_ENABLED = True              # set False for the no-SMC seasonality/intensity calibration
SMC_START = {"upper_west": 2015, "upper_east": 2016, "northern": 2019}
# IRS coverage(year): explicit because Upper East was a 2013-14 PULSE (forward-fill would be wrong).
IRS_SCHEDULE = {
    "upper_east": {2013: 0.90, 2014: 0.90},                       # AGAMal pulse then withdrawn
    "upper_west": {y: 0.30 for y in range(2014, END_YEAR + 1)},   # AGAMal: district-fraction effective coverage (not 90% region-wide)
    "northern":   {**{y: 0.30 for y in range(2008, 2013)},        # PMI partial, district-fraction
                   **{y: 0.15 for y in range(2013, 2017)},
                   **{y: 0.25 for y in range(2017, END_YEAR + 1)}},
}


def day(year, doy=1):
    return (year - SIM_START_YEAR) * 365 + (doy - 1)


def coverage_schedule(region):
    """Annual forward-filled coverages (itn, careseek, smc) from the survey data."""
    df = pd.read_csv("data/three_region_data.csv", comment="#")
    d = df[df.region == region].set_index("year").sort_index()
    sched = {}
    for y in range(SIM_START_YEAR, proj_end() + 1):
        yy = max(2011, min(y, END_YEAR))          # run-in=2011; projection years hold 2022
        past = d[d.index <= yy]
        row = past.iloc[-1] if len(past) else d.iloc[0]
        sched[y] = dict(itn=float(row.itn_u5), careseek=float(row.careseek))
    return sched


def itn_campaign_coverage(region):
    """Coverage distributed at each mass campaign = ITN usage from the nearest DHS
    survey (ties broken toward the post-campaign survey)."""
    df = pd.read_csv("data/three_region_data.csv", comment="#")
    d = df[df.region == region].set_index("year")
    surv = sorted(d.index)
    out = {}
    for cy in ITN_CAMPAIGN_YEARS:
        closest = min(surv, key=lambda sy: (abs(sy - cy), -(sy >= cy), -sy))
        out[cy] = float(d.loc[closest, "itn_u5"])
    return out


def build_campaign(region):
    def bc():
        import emod_api.campaign as campaign
        campaign.set_schema(manifest.schema_file)
        # steady low importation throughout, so the node can't unrealistically eliminate
        add_outbreak_individual(
            campaign, start_day=1, target_num_individuals=IMPORT_PER_CYCLE,
            repetitions=int(n_years() * 365 / IMPORT_INTERVAL),
            timesteps_between_repetitions=IMPORT_INTERVAL,
            target_age_min=0, target_age_max=100,
        )
        sched = coverage_schedule(region)
        smc_start = SMC_START[region]
        irs = IRS_SCHEDULE.get(region, {})

        # ITN: 3-yearly MASS CAMPAIGNS (not annual). Each campaign distributes nets to a
        # coverage taken from the nearest DHS survey; Weibull net retention (~2.4-yr median,
        # paper k=2.3) then decays usage between campaigns -> realistic saw-tooth.
        itn_cov = itn_campaign_coverage(region)
        for cy, ccov in itn_cov.items():
            if cy < SIM_START_YEAR:               # campaigns before the sim start can't be scheduled
                continue
            add_scheduled_usage_dependent_bednet(
                campaign, start_day=day(cy, ITN_DOY), demographic_coverage=ccov,
                blocking_initial_effect=ES.ITN_BLOCK, killing_initial_effect=ES.ITN_KILL,
                blocking_decay_time_constant=ES.ITN_BLOCK_DECAY,
                killing_decay_time_constant=ES.ITN_KILL_DECAY,
                age_dependence=ES.ITN_AGE_USAGE,  # nets to all ages; usage lower in school-age/adults
                discard_config={"Expiration_Period_Distribution": "WEIBULL_DISTRIBUTION",
                                "Expiration_Period_Kappa": 2.3, "Expiration_Period_Lambda": 912},
                dont_allow_duplicates=False,      # a mass campaign re-nets everyone
            )

        for y in range(SIM_START_YEAR, proj_end() + 1):
            cov = sched[y]
            # Case management: treat clinical cases at careseeking coverage with AL
            add_treatment_seeking(
                campaign, start_day=day(y, 1), drug=ES.CM_DRUG, duration=365,
                targets=[{"trigger": "NewClinicalCase", "coverage": cov["careseek"],
                          "agemin": 0, "agemax": 100, "rate": ES.CM_RATE}],
            )
            # SMC. Historical years use current policy (4 cycles, 3-59mo); projection years
            # (>2022) use the chosen SCENARIO (extra October cycle and/or older ages).
            if SMC_ENABLED and y >= smc_start:
                p = SCENARIO["baseline"] if y <= END_YEAR else SCENARIO[SMC_SCENARIO]
                if y <= END_YEAR:
                    # Historical (calibrated): persistent 60%-reached IP subset x 90%/cycle.
                    for c in range(p["cycles"]):
                        add_drug_campaign(
                            campaign, campaign_type="SMC", drug_code="SPA",
                            start_days=[day(y, SMC_FIRST_DOY + c * SMC_INTERVAL)],
                            coverage=ES.SMC_COVERAGE, repetitions=1,
                            tsteps_btwn_repetitions=SMC_INTERVAL,
                            target_group={"agemin": ES.SMC_AGE_MIN, "agemax": p["age_max"]},
                            ind_property_restrictions=[{"SMCReached": "Y"}],   # persistent reached subset
                        )
                else:
                    # Projection: literature per-cycle coverage applied by age band (no IP).
                    # Under-5 always covered; older bands only if the scenario extends to them.
                    cU5, c510, c1015 = ES.SMC_PROJ_COVERAGE[y]
                    bands = [(ES.SMC_AGE_MIN, 5.0, cU5)]
                    if p["age_max"] >= 10.0:
                        bands.append((5.0, 10.0, c510))
                    if p["age_max"] >= 15.0:
                        bands.append((10.0, 15.0, c1015))
                    for amin, amax, cov in bands:
                        for c in range(p["cycles"]):
                            add_drug_campaign(
                                campaign, campaign_type="SMC", drug_code="SPA",
                                start_days=[day(y, SMC_FIRST_DOY + c * SMC_INTERVAL)],
                                coverage=cov, repetitions=1,
                                tsteps_btwn_repetitions=SMC_INTERVAL,
                                target_group={"agemin": amin, "agemax": amax},
                            )
            # IRS per region timeline (killing depends on insecticide era, non-cross-resistant)
            if irs.get(y, 0) > 0:
                add_scheduled_irs_housing_modification(
                    campaign, start_day=day(y, IRS_DOY), demographic_coverage=irs[y],
                    killing_initial_effect=ES.IRS_KILL[region],
                    killing_box_duration=ES.IRS_BOX_DURATION,
                    killing_decay_time_constant=90,
                )
        return campaign
    return bc


def build_config(x, state_filename, run_number=1):
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
        # pickup burned-in population
        config.parameters.Serialized_Population_Reading_Type = "READ"
        config.parameters.Serialized_Population_Path = "Assets"
        config.parameters.Serialized_Population_Filenames = [state_filename]
        config.parameters.Enable_Random_Generator_From_Serialized_Population = 0
        config.parameters.Simulation_Duration = n_years() * 365
        config.parameters.Run_Number = run_number
        config.parameters.x_Temporary_Larval_Habitat = x
        config.parameters.Enable_Default_Reporting = 1
        return config
    return cfg


def build_task(region, x, state_path, run_number=1):
    # state_path's basename becomes the in-Assets filename; pass a uniquely-named
    # (staged) copy when several x-states must share one experiment.
    state_filename = os.path.basename(state_path)
    task = EMODTask.from_default2(
        config_path="config.json",
        eradication_path=manifest.eradication_path,
        schema_path=manifest.schema_file,
        param_custom_cb=build_config(x, state_filename, run_number),
        campaign_builder=build_campaign(region),
        demog_builder=lambda: burnin.build_demographics(region),
        ep4_custom_cb=None,
    )
    wdir = RC.weather_dir(region)
    for f in sorted(os.listdir(wdir)):
        task.common_assets.add_asset(os.path.join(wdir, f))
    task.common_assets.add_asset(state_path)
    # monthly under-5 PfPR at a microscopy-like detection threshold
    add_malaria_summary_report(
        task, manifest, start_day=0, end_day=n_years() * 365,
        reporting_interval=30, age_bins=burnin.AGE_BINS,
        parasite_detection_threshold=40, add_hrp2_prevalence=True,
        hrp2_detection_threshold=5, max_number_reports=250,
    )
    return task


def main():
    region = RC.check(sys.argv[1])
    x = float(sys.argv[2])
    state_path = sys.argv[3] if len(sys.argv) > 3 else None
    if not state_path:
        import glob
        hits = sorted(glob.glob(os.path.join(manifest.job_directory,
                      f"e_ghana_burnin_{region}_50yr_*", "*", "output", "state-*.dtk")),
                      key=os.path.getmtime, reverse=True)
        if not hits:
            raise SystemExit(f"no burn-in state for {region}; pass state_path")
        state_path = hits[0]
    print(f"Historical {region} 2008-2022, x={x}, pickup={state_path}")

    task = build_task(region, x, state_path)
    exp = Experiment.from_task(task, name=f"ghana_hist_{region}")
    exp.run(platform=Platform("Container", job_directory=manifest.job_directory, max_job=RC.MAX_JOB),
            wait_until_done=True)
    print("Status:", exp.status, "| Succeeded:", exp.succeeded)


if __name__ == "__main__":
    main()
