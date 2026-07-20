"""
Intervention campaign builders for the Navrongo policy study:
  - SMC   (seasonal malaria chemoprevention, SPAQ)
  - RTS,S  (pre-erythrocytic vaccine, modeled AcquisitionBlocking)
  - R21    (pre-erythrocytic vaccine, higher seasonal efficacy)

All timings are day-of-year within each intervention year; the builders repeat
the schedule annually across the intervention period.

NOTE: efficacy/waning and coverage values below are evidence-INFORMED defaults
(RTS,S Phase 3; R21/Matrix-M Nanoro) but PROVISIONAL — to be finalized against
the literature you choose. They are collected here as named constants for easy tuning.
"""
from emodpy_malaria.interventions.drug_campaign import add_drug_campaign
from emodpy_malaria.interventions.vaccine import add_scheduled_vaccine

# ---- Navrongo seasonal timing (day-of-year) --------------------------------
# Rains Jun-Sep, EIR peak Oct-Nov. SMC = 4 monthly cycles Jun-Sep (Ghana schedule).
SMC_FIRST_CYCLE_DOY = 152        # ~1 June
SMC_CYCLES = 4
SMC_CYCLE_INTERVAL = 30          # days between cycles -> Jun/Jul/Aug/Sep
VACCINE_DOSE_DOY = 121           # ~1 May, before SMC starts (seasonal dose)

# ---- Coverage --------------------------------------------------------------
SMC_COVERAGE = 0.90
VACCINE_COVERAGE = 0.80

# ---- Target ages (years) ---------------------------------------------------
SMC_AGE_MIN, SMC_AGE_MAX = 0.25, 5.0        # 3-59 months
VAX_AGE_MIN, VAX_AGE_MAX = 0.25, 5.0        # simplification: seasonal child campaign

# ---- Vaccine efficacy/waning (AcquisitionBlocking) -------------------------
# initial_effect = per-bite reduction in infection acquisition; box then exp decay.
RTSS_PARAMS = dict(initial_effect=0.55, box_duration=30, decay_time_constant=365)
R21_PARAMS  = dict(initial_effect=0.75, box_duration=30, decay_time_constant=365)


def add_smc(campaign, n_years, coverage=SMC_COVERAGE):
    """SPAQ SMC: 4 monthly cycles each transmission season, children 3-59 mo."""
    for y in range(n_years):
        add_drug_campaign(
            campaign,
            campaign_type="SMC",
            drug_code="SPA",
            start_days=[y * 365 + SMC_FIRST_CYCLE_DOY],
            coverage=coverage,
            repetitions=SMC_CYCLES,
            tsteps_btwn_repetitions=SMC_CYCLE_INTERVAL,
            target_group={"agemin": SMC_AGE_MIN, "agemax": SMC_AGE_MAX},
        )
    return campaign


def _add_vaccine(campaign, n_years, params, coverage=VACCINE_COVERAGE):
    """One seasonal dose (with annual boosting) before each transmission season."""
    add_scheduled_vaccine(
        campaign,
        start_day=VACCINE_DOSE_DOY,
        demographic_coverage=coverage,
        repetitions=n_years,
        timesteps_between_repetitions=365,
        target_age_min=VAX_AGE_MIN,
        target_age_max=VAX_AGE_MAX,
        vaccine_type="AcquisitionBlocking",
        vaccine_initial_effect=params["initial_effect"],
        vaccine_box_duration=params["box_duration"],
        vaccine_decay_time_constant=params["decay_time_constant"],
    )
    return campaign


def add_rtss(campaign, n_years, coverage=VACCINE_COVERAGE):
    return _add_vaccine(campaign, n_years, RTSS_PARAMS, coverage)


def add_r21(campaign, n_years, coverage=VACCINE_COVERAGE):
    return _add_vaccine(campaign, n_years, R21_PARAMS, coverage)
