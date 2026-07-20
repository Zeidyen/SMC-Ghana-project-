"""
Efficiency analysis of the projection: absolute cases averted and cases averted
PER ADDITIONAL SMC COURSE delivered (the budget-relevant metric). Re-reads the
existing projection experiment (no new sims). Paired by seed -> mean [95% CI].

    python efficiency.py <region>
"""
import os
import sys
import glob
import json

import numpy as np
import pandas as pd

import manifest
import historical as H
import effect_sizes as ES

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"5cycle": "SMC-5 (U5)", "age10": "SMC-4 (U10)", "age15": "SMC-4 (U15)",
          "5cycle_age10": "SMC-5 (U10)", "5cycle_age15": "SMC-5 (U15)"}
SEEDS = list(range(1, 61))
PROJ_YEARS = 5
# age-bin indices for U5, 5-10, 10-15 (bins [5,10,15,25,50,125])
U15_BINS = [0, 1, 2]
ELIGIBLE_BINS = {"baseline": [0], "5cycle": [0], "age10": [0, 1], "age15": [0, 1, 2],
                 "5cycle_age10": [0, 1], "5cycle_age15": [0, 1, 2]}
CYCLES = {"baseline": 4, "5cycle": 5, "age10": 4, "age15": 4, "5cycle_age10": 5, "5cycle_age15": 5}
COURSE_PER_CHILD = ES.SMC_REACHED_FRAC * ES.SMC_COVERAGE   # 0.6 x 0.9 = per-child per-cycle probability


def load(region):
    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    data = {sc: {} for sc in SCENARIOS}   # data[scen][seed] = dict(inc=array_by_bin, pop=array_by_bin)
    for entry in os.scandir(exp):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; sr = json.load(open(rep))
        inc = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])
        pop = np.array(sr["DataByTimeAndAgeBins"]["Average Population by Age Bin"])
        tt = sr["DataByTime"]["Time Of Report"][:len(inc)]
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        m = (yr >= 2023) & (yr <= 2022 + PROJ_YEARS)
        data[tg["scen"]][int(tg["seed"])] = dict(inc=inc[m].mean(axis=0), pop=pop[m].mean(axis=0))
    return data


def report(region):
    d = load(region)
    print(f"\n=== {region} projection efficiency 2023-2027 (mean [95% CI], {len(SEEDS)} seeds, per 1000 under-15/yr) ===")
    print(f"{'policy':14s} {'cases averted/1000/yr (U15)':>28s} {'extra courses/1000/yr':>22s} {'cases averted / 100 courses':>28s}")
    print("-" * 96)
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        av_per, crs_per, eff = [], [], []
        for s in SEEDS:
            if s not in d[sc] or s not in d["baseline"]:
                continue
            b, x = d["baseline"][s], d[sc][s]
            pop_u15 = x["pop"][U15_BINS].sum()
            # absolute cases averted per year across U15 = sum_bin (dInc * pop)
            averted = sum((b["inc"][i] - x["inc"][i]) * x["pop"][i] for i in U15_BINS)
            # SMC courses delivered per year (child-cycles) for each arm
            crs_base = CYCLES["baseline"] * COURSE_PER_CHILD * x["pop"][ELIGIBLE_BINS["baseline"]].sum()
            crs_scen = CYCLES[sc] * COURSE_PER_CHILD * x["pop"][ELIGIBLE_BINS[sc]].sum()
            extra = crs_scen - crs_base
            av_per.append(1000 * averted / pop_u15)
            crs_per.append(1000 * extra / pop_u15)
            eff.append(100 * averted / extra if extra > 0 else np.nan)

        def ci(v):
            v = np.array(v); return f"{np.nanmean(v):6.1f} [{np.nanpercentile(v,2.5):5.1f},{np.nanpercentile(v,97.5):5.1f}]"
        print(f"{LABELS[sc]:14s} {ci(av_per):>28s} {ci(crs_per):>22s} {ci(eff):>28s}")
    print("\n(efficiency = malaria cases averted per 100 ADDITIONAL SMC child-courses; higher = better value)")


if __name__ == "__main__":
    report(sys.argv[1])
