"""
Historical fit check: compare the model's under-5 RDT (HRP2) prevalence over
2011-2022 to the survey targets, for the CURRENT projection experiment's baseline
sims. Run after the first sims complete to confirm the ITN age-usage change did
not break the calibration before trusting the full run.

    python validate_rdt.py <region>
"""
import os
import sys
import glob
import json

import numpy as np
import pandas as pd

import manifest
import historical as H

SURVEY_YEARS = [2011, 2014, 2016, 2019, 2022]


def main(region):
    df = pd.read_csv("data/three_region_data.csv", comment="#")
    obs = df[df.region == region].set_index("year")["pfpr_rdt"]

    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    # collect under-5 RDT annual means from baseline sims (any seed)
    per_year = {y: [] for y in SURVEY_YEARS}
    n = 0
    for entry in os.scandir(exp):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        if json.load(open(t))["tags"].get("scen") != "baseline":
            continue
        sr = json.load(open(rep))
        rdt = np.array(sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"])[:, 0]   # bin 0 = under-5
        tt = np.array(sr["DataByTime"]["Time Of Report"][:len(rdt)])
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        for Y in SURVEY_YEARS:
            m = (yr == Y)
            if m.any():
                per_year[Y].append(rdt[m].mean())
        n += 1

    if n == 0:
        print("No completed baseline sims yet — wait for the first wave.")
        return
    print(f"\n=== {region} historical under-5 RDT (HRP2) fit vs survey  [{n} baseline sim(s)] ===")
    print(f"{'year':>6} {'model':>8} {'survey':>8} {'diff':>8}")
    errs = []
    for Y in SURVEY_YEARS:
        if not per_year[Y]:
            continue
        m = float(np.mean(per_year[Y])); o = float(obs.get(Y, np.nan)); d = m - o
        errs.append(d)
        print(f"{Y:>6} {m:>8.3f} {o:>8.3f} {d:>+8.3f}")
    errs = np.array(errs)
    print(f"\nmean signed error: {errs.mean():+.3f}  |  mean |error|: {np.abs(errs).mean():.3f}")
    print("(positive = model OVER-predicts RDT; watch 2016-2022 where SMC+ITN act)")


if __name__ == "__main__":
    main(sys.argv[1])
