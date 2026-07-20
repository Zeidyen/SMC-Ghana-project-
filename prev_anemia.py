"""
Two extra Upper-East endpoints from the existing projection (no re-sim):
  - projected parasite PREVALENCE reduction (RDT/HRP2 and microscopy) by age band
    -- the natural output since transmission was calibrated to prevalence.
  - childhood ANAEMIA (severe + moderate) reduction and cases averted -- a second
    morbidity endpoint SMC is known to reduce.
Pooled across seeds with seed-bootstrap 95% CIs.

    python prev_anemia.py <region>
"""
import os
import sys
import json
import numpy as np
import pandas as pd

import manifest
import historical as H

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"5cycle": "SMC-5 (U5)", "age10": "SMC-4 (U10)", "age15": "SMC-4 (U15)",
          "5cycle_age10": "SMC-5 (U10)", "5cycle_age15": "SMC-5 (U15)"}
SEEDS = list(range(1, 61))
BANDS = {"U5": [0], "5-10": [1], "10-15": [2], "U15": [0, 1, 2]}
PROJ = (2023, 2027)


def load(region):
    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    d = {sc: {} for sc in SCENARIOS}
    for e in os.scandir(exp):
        if not e.is_dir() or e.name == "Assets":
            continue
        t = os.path.join(e.path, "tags.json"); rep = os.path.join(e.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; sr = json.load(open(rep))
        D = sr["DataByTimeAndAgeBins"]
        arrs = {k: np.array(D[k]) for k in ["PfPR by Age Bin-HRP2", "PfPR by Age Bin",
                "Annual Severe Anemia by Age Bin", "Annual Moderate Anemia by Age Bin",
                "Average Population by Age Bin"]}
        tt = np.array(sr["DataByTime"]["Time Of Report"][:len(arrs["Average Population by Age Bin"])])
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        m = (yr >= PROJ[0]) & (yr <= PROJ[1])
        d[tg["scen"]][int(tg["seed"])] = {k: v[m].mean(axis=0) for k, v in arrs.items()}
    return d


def pooled(d, sc, idx, key, seeds, weighted, nboot=2000):
    """% reduction vs BAU. weighted=True -> pop-weighted rate (prevalence);
    False -> summed cases (anemia incidence x pop)."""
    pop = "Average Population by Age Bin"
    if weighted:
        b = np.array([(d["baseline"][s][key][idx] * d["baseline"][s][pop][idx]).sum() /
                      d["baseline"][s][pop][idx].sum() for s in seeds])
        x = np.array([(d[sc][s][key][idx] * d[sc][s][pop][idx]).sum() /
                      d[sc][s][pop][idx].sum() for s in seeds])
    else:
        b = np.array([(d["baseline"][s][key][idx] * d["baseline"][s][pop][idx]).sum() for s in seeds])
        x = np.array([(d[sc][s][key][idx] * d[sc][s][pop][idx]).sum() for s in seeds])
    np.random.seed(0)
    f = lambda ix: 100 * (b[ix].sum() - x[ix].sum()) / b[ix].sum() if b[ix].sum() > 0 else np.nan
    pt = f(np.arange(len(seeds)))
    bs = np.array([f(np.random.randint(0, len(seeds), len(seeds))) for _ in range(nboot)])
    bs = bs[np.isfinite(bs)]
    if len(bs) == 0:
        return pt, np.nan, np.nan
    return pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def report(region):
    d = load(region)
    seeds = [s for s in SEEDS if all(s in d[sc] for sc in SCENARIOS)]
    fmt = lambda v: f"{v[0]:5.1f} [{v[1]:4.0f},{v[2]:4.0f}]"

    for key, name, wt in [("PfPR by Age Bin-HRP2", "RDT/HRP2 PREVALENCE", True),
                          ("PfPR by Age Bin", "MICROSCOPY PREVALENCE", True)]:
        print(f"\n=== {region} {name}: % reduction vs BAU 2023-2027 ({len(seeds)} seeds) ===")
        print(f"{'scenario':14s}" + "".join(f"{b:>16s}" for b in BANDS))
        for sc in SCENARIOS:
            if sc == "baseline":
                continue
            cells = [fmt(pooled(d, sc, np.array(idx), key, seeds, wt)) for idx in BANDS.values()]
            print(f"{LABELS[sc]:14s}" + "".join(f"{c:>16s}" for c in cells))

    # anaemia (severe+moderate) cases averted per 1000 U15/yr, scaled comment
    print(f"\n=== {region} childhood ANAEMIA (severe+moderate) cases averted /1000 U15/yr ===")
    u15 = np.array([0, 1, 2])
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        av = []
        for s in seeds:
            pop = d[sc][s]["Average Population by Age Bin"]
            d_an = sum((d["baseline"][s][k][u15] - d[sc][s][k][u15]) * pop[u15]
                       for k in ["Annual Severe Anemia by Age Bin", "Annual Moderate Anemia by Age Bin"]).sum()
            av.append(1000 * d_an / pop[u15].sum())
        m = np.mean(av); lo, hi = np.percentile(av, [2.5, 97.5])
        print(f"  {LABELS[sc]:14s} {m:6.1f} [{lo:5.1f},{hi:5.1f}]")


if __name__ == "__main__":
    report(sys.argv[1])
