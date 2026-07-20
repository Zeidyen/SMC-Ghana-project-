"""
Year-on-year projection export (annual averages) from the completed 20k run.
For each projection year x scenario x age band: mean clinical & severe incidence
per 1000/yr (mean + 95% CI across seeds) and % reduction vs BAU that year.

Writes:
  data/projection_annual_<region>.csv     -- tidy long format (one row per year/scenario/band/metric)
  data/projection_annual_<region>_wide.csv -- wide: clinical incidence by year, scenarios as columns

    python export_annual.py <region>
"""
import os
import sys
import glob
import json

import numpy as np
import pandas as pd

import manifest
import historical as H

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"baseline": "BAU: SMC-4 (U5)", "5cycle": "SMC-5 (U5)", "age10": "SMC-4 (U10)",
          "age15": "SMC-4 (U15)", "5cycle_age10": "SMC-5 (U10)", "5cycle_age15": "SMC-5 (U15)"}
SEEDS = list(range(1, 61))
BANDS = {"U5": [0], "5-10": [1], "10-15": [2], "U15": [0, 1, 2]}
PROJ = list(range(2023, 2028))
FIELDS = {"clinical": "Annual Clinical Incidence by Age Bin",
          "severe": "Annual Severe Incidence by Age Bin"}


def load(region):
    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    # d[scen][seed][metric] = DataFrame(year -> {band: annual-mean incidence per 1000})
    d = {sc: {} for sc in SCENARIOS}
    for entry in os.scandir(exp):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; sr = json.load(open(rep))
        tt = np.array(sr["DataByTime"]["Time Of Report"])
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        pop = np.array(sr["DataByTimeAndAgeBins"]["Average Population by Age Bin"])
        rec = {}
        for metric, field in FIELDS.items():
            arr = np.array(sr["DataByTimeAndAgeBins"][field]); y = yr[:len(arr)]
            per_year = {}
            for Y in PROJ:
                m = (y == Y)
                # POP-WEIGHTED rate for multi-bin groups (cases/pop); reduces to the
                # plain band rate for single bins. Summing rates over-counts groups ~Nx.
                per_year[Y] = {b: 1000 * (arr[m][:, idx] * pop[m][:, idx]).sum(axis=1).mean()
                               / pop[m][:, idx].sum(axis=1).mean() for b, idx in BANDS.items()}
            rec[metric] = per_year
        d[tg["scen"]][int(tg["seed"])] = rec
    return d


def ci(vals):
    v = np.array(vals); return v.mean(), np.percentile(v, 2.5), np.percentile(v, 97.5)


def export(region):
    d = load(region)
    seeds = [s for s in SEEDS if all(s in d[sc] for sc in SCENARIOS)]
    rows = []
    for metric in FIELDS:
        for Y in PROJ:
            for sc in SCENARIOS:
                for b in BANDS:
                    vals = [d[sc][s][metric][Y][b] for s in seeds]
                    m, lo, hi = ci(vals)
                    # % reduction vs BAU that year (paired by seed)
                    if sc == "baseline":
                        red = redlo = redhi = np.nan
                    else:
                        pr = [100 * (d["baseline"][s][metric][Y][b] - d[sc][s][metric][Y][b])
                              / d["baseline"][s][metric][Y][b] if d["baseline"][s][metric][Y][b] > 0 else np.nan
                              for s in seeds]
                        red, redlo, redhi = ci(pr)
                    rows.append(dict(year=Y, scenario=LABELS[sc], age_band=b, metric=metric,
                                     incidence_per1000=round(m, 1), ci_lo=round(lo, 1), ci_hi=round(hi, 1),
                                     pct_reduction_vs_BAU=round(red, 1) if red == red else "",
                                     red_lo=round(redlo, 1) if redlo == redlo else "",
                                     red_hi=round(redhi, 1) if redhi == redhi else ""))
    df = pd.DataFrame(rows)
    long_path = f"data/projection_annual_{region}.csv"
    df.to_csv(long_path, index=False)

    # wide: clinical incidence, year x band rows, scenarios as columns
    cw = df[df.metric == "clinical"].pivot_table(index=["year", "age_band"], columns="scenario",
                                                 values="incidence_per1000", aggfunc="first")
    cw = cw[[LABELS[s] for s in SCENARIOS]]           # column order
    wide_path = f"data/projection_annual_{region}_wide.csv"
    cw.to_csv(wide_path)

    print(f"wrote {long_path} ({len(df)} rows) and {wide_path}")
    print("\n--- preview: clinical incidence per 1000/yr, U15, by year x scenario ---")
    print(df[(df.metric == "clinical") & (df.age_band == "U15")]
          .pivot_table(index="year", columns="scenario", values="incidence_per1000", aggfunc="first")[[LABELS[s] for s in SCENARIOS]].to_string())
    print("\n--- preview: clinical % reduction vs BAU, U15, by year x scenario ---")
    print(df[(df.metric == "clinical") & (df.age_band == "U15") & (df.scenario != "BAU")]
          .pivot_table(index="year", columns="scenario", values="pct_reduction_vs_BAU", aggfunc="first").to_string())


if __name__ == "__main__":
    export(sys.argv[1])
