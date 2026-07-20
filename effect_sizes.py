"""
Literature-sourced intervention effect sizes for the northern-Ghana EMOD models.
Every value carries a source; see data/effect_sizes_sources.md for the full table.

KEY CONTEXT: northern Ghana has HIGH pyrethroid resistance, so pyrethroid ITNs
(and pyrethroid IRS) mostly provide personal-protection BLOCKING with little
KILLING. Organophosphate (Actellic) and clothianidin IRS are NOT cross-resistant,
so they retain high killing -- these plus SMC are the real transmission reducers.
"""

# ---- ITN (pyrethroid, resistance-adjusted for northern Ghana) ---------------
# Churcher 2016 eLife (bioassay->hut-mortality); Ozodiegwu 2023 Malar J (EMOD);
# emodpy Bednet defaults (susceptible block/kill = 0.9/0.6).
ITN_BLOCK = 0.75              # personal protection, eroded by resistance
ITN_KILL = 0.15              # crushed by resistance (susceptible would be 0.6)
ITN_BLOCK_DECAY = 730         # days (~2 yr)
ITN_KILL_DECAY = 1460         # days (~4 yr)
ITN_RETENTION_DAYS = 700      # net loss/discard mean (~1.9 yr); Bertozzi-Villa 2021 / PMI Ghana
# Age-dependent net USAGE multiplier (nets are distributed to all ages, but use
# varies by age). Under-5 = 1.0 keeps the calibrated under-5 protection intact;
# school-age children use nets least ("school-age dip"), adults intermediate.
# Pattern per DHS age-use curves / Bertozzi-Villa 2021. Multiplies the itn_u5 rate.
ITN_AGE_USAGE = {"Times":  [0,   5,   6,    15,   18,   125],
                 "Values": [1.0, 1.0, 0.65, 0.65, 0.80, 0.80]}

# ---- IRS killing by region (reflects insecticide era, non-cross-resistant) --
# Owusu 2021 (Actellic ~6-9 mo, kill ~0.9), Oxborough 2019 (clothianidin),
# Churcher 2016 (pyrethroid under resistance ~weak). Upper East 2013-14 AGAMal
# spray was moderate (obs 2014 stayed ~0.12, not zero) -> killing ~0.5.
IRS_KILL = {
    "upper_east": 0.50,       # AGAMal pulse 2013-14, moderate (uncertain insecticide)
    "upper_west": 0.60,       # AGAMal sustained
    "northern":   0.85,       # PMI Actellic/clothianidin (organophosphate/neonic)
}
IRS_BOX_DURATION = 200        # days of high killing before decay (~6.5 mo)

# ---- SMC (SPAQ) ------------------------------------------------------------
# Cairns 2021 PLoS Med / ACCESS-SMC 2020 Lancet: ~88% clinical protection days 0-28,
# ~61% days 29-42; ~65% end-of-season prevalence reduction. EMOD default SPAQ drug
# params (amodiaquine decay T2=37.5 d) reproduce the ~28-day window -> use drug_code "SPA".
# PERSISTENT reach via an Individual Property: SMC_REACHED_FRAC of children are
# reliably reached (get SMC every cycle at SMC_COVERAGE); the rest are never reached
# and sustain cases through the season (building immunity) -> no synchronized rebound.
SMC_REACHED_FRAC = 0.60         # fixed fraction reliably reached (calibratable)
SMC_COVERAGE = 0.90             # per-cycle coverage WITHIN the reached subset
SMC_AGE_MIN, SMC_AGE_MAX = 0.25, 5.0

# --- PROJECTION per-cycle coverage by age band (2023-2027), literature-anchored ---
# Applied directly (independent per cycle) in projection years, replacing the fixed
# 60%-reached IP used for the calibrated historical period. Metric = per-cycle
# effective coverage (EMOD generates full-course endogenously across cycles).
#   U5    : 0.87 flat -- established Ghana level, Upper East 2024 survey 87%/cycle
#           (Abdul-Karim et al., Malaria J 2025).
#   5-10  : ramp 0.75->0.85 -- newly-extended band matures over ~3y; Senegal 5-9y
#           reached 87-96% door-to-door (Ba 2018; Cisse 2016, PLoS Med).
#   10-15 : ramp 0.65->0.75 -- ASSUMPTION, no direct SPAQ data; community reach
#           hardest for this band (school/farm absence: Moukenet 2022; Ibinaiye 2024).
SMC_PROJ_COVERAGE = {
    #  year:  U5    5-10  10-15
    2023: (0.87, 0.75, 0.65),
    2024: (0.87, 0.80, 0.70),
    2025: (0.87, 0.85, 0.75),
    2026: (0.87, 0.85, 0.75),
    2027: (0.87, 0.85, 0.75),
}

# ---- Case management (AL / artemether-lumefantrine) ------------------------
# Abuaku 2019 Malar J: PCR-corrected day-28 cure Ghana ~0.96 (Navrongo 98%, Yendi 96%).
# Effective coverage = careseek x ACT-receipt x adherence x cure (Galactionova 2015).
CM_DRUG = ["Artemether", "Lumefantrine"]
CM_CURE = 0.96
CM_ACT_ADHERENCE = 0.81       # fraction of treated who complete AL (Galactionova)
CM_RATE = 0.3                 # ~3.3-day mean treatment delay (Ozodiegwu 2023)
