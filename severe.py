"""
Severe-malaria outcomes from the existing projection runs (no re-sim). Severe
cases are the mortality-relevant endpoint for SMC. Reports, by age band:
  - absolute severe incidence per 1000/yr (baseline + scenarios)
  - % reduction vs baseline (paired by seed)
  - severe cases averted per 100 additional SMC courses (efficiency)
All with 95% CIs across seeds. Also emits a two-panel figure.

    python severe.py <region>
"""
import os
import sys
import glob
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 18})

import manifest
import historical as H
import effect_sizes as ES

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"baseline": "BAU: SMC-4 (U5)", "5cycle": "SMC-5 (U5)", "age10": "SMC-4 (U10)",
          "age15": "SMC-4 (U15)", "5cycle_age10": "SMC-5 (U10)", "5cycle_age15": "SMC-5 (U15)"}
SEEDS = list(range(1, 61))
PROJ_YEARS = 5
BANDS = {"U5": [0], "5-10": [1], "10-15": [2]}
COLORS = {"U5": "#d62728", "5-10": "#1f77b4", "10-15": "#2ca02c"}
U15_BINS = [0, 1, 2]
ELIGIBLE_BINS = {"baseline": [0], "5cycle": [0], "age10": [0, 1], "age15": [0, 1, 2],
                 "5cycle_age10": [0, 1], "5cycle_age15": [0, 1, 2]}
CYCLES = {"baseline": 4, "5cycle": 5, "age10": 4, "age15": 4, "5cycle_age10": 5, "5cycle_age15": 5}
COURSE_PER_CHILD = ES.SMC_REACHED_FRAC * ES.SMC_COVERAGE
FIELD = "Annual Severe Incidence by Age Bin"


def load(region):
    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    d = {sc: {} for sc in SCENARIOS}
    for entry in os.scandir(exp):
        if not entry.is_dir() or entry.name == "Assets":
            continue
        t = os.path.join(entry.path, "tags.json"); rep = os.path.join(entry.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        tg = json.load(open(t))["tags"]; sr = json.load(open(rep))
        sev = np.array(sr["DataByTimeAndAgeBins"][FIELD])
        pop = np.array(sr["DataByTimeAndAgeBins"]["Average Population by Age Bin"])
        tt = sr["DataByTime"]["Time Of Report"][:len(sev)]
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        m = (yr >= 2023) & (yr <= 2022 + PROJ_YEARS)
        d[tg["scen"]][int(tg["seed"])] = dict(
            sev={b: sev[m][:, idx].sum(axis=1).mean() for b, idx in BANDS.items()},
            pop=pop[m].mean(axis=0))
    return d


def stat(v):
    v = np.array(v); return v.mean(), *np.percentile(v, [2.5, 97.5])


def report(region):
    d = load(region)
    seeds = [s for s in SEEDS if all(s in d[sc] for sc in SCENARIOS)]

    # Severe is a RARE event: per-seed % reductions divide by tiny/zero baselines
    # and are unusable. Use POOLED severe cases (rate x pop, summed across seeds)
    # for the point estimate, with a seed-bootstrap 95% CI -- the correct estimator
    # for rare counts. BIN maps a band key to its age-bin index.
    BIN = {"U5": 0, "5-10": 1, "10-15": 2}
    np.random.seed(0)

    def band_cases(scen, s, idx):
        return sum(d[scen][s]["sev"][k] * d[scen][s]["pop"][BIN[k]] for k in idx)

    def pooled_reduction(sc, idx, nboot=3000):
        base = np.array([band_cases("baseline", s, idx) for s in seeds])
        scen = np.array([band_cases(sc, s, idx) for s in seeds])

        def pct(sel):
            B = base[sel].sum()
            return 100 * (B - scen[sel].sum()) / B if B > 0 else np.nan
        pt = pct(np.arange(len(seeds)))
        n = len(seeds)
        bs = np.array([pct(np.random.randint(0, n, n)) for _ in range(nboot)])
        bs = bs[~np.isnan(bs)]
        return pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)

    print(f"\n=== {region} SEVERE malaria 2023-2027 (pooled % reduction, seed-bootstrap 95% CI, {len(seeds)} seeds) ===")
    print("% reduction vs baseline:")
    print(f"{'scenario':14s} " + " ".join(f"{b:>16s}" for b in BANDS) + f"{'U15':>16s}")
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        cells = []
        for b in list(BANDS) + ["U15"]:
            idx = [b] if b in BANDS else ["U5", "5-10", "10-15"]
            mu, lo, hi = pooled_reduction(sc, idx)
            cells.append(f"{mu:5.1f} [{lo:4.0f},{hi:4.0f}]")
        print(f"{LABELS[sc]:14s} " + " ".join(f"{c:>16s}" for c in cells))

    print("\nsevere cases averted / 100 extra SMC courses (U15):")
    print(f"{'scenario':14s} {'severe averted/1000/yr':>24s} {'per 100 courses':>18s}")
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        av, eff = [], []
        for s in seeds:
            x = d[sc][s]; b = d["baseline"][s]
            pop_u15 = x["pop"][U15_BINS].sum()
            # weight each band's severe rate by its population to get absolute cases averted
            av_abs = sum((b["sev"][k] - x["sev"][k]) * x["pop"][i] for k, i in zip(BANDS, U15_BINS))
            crs_base = CYCLES["baseline"] * COURSE_PER_CHILD * x["pop"][ELIGIBLE_BINS["baseline"]].sum()
            crs_scen = CYCLES[sc] * COURSE_PER_CHILD * x["pop"][ELIGIBLE_BINS[sc]].sum()
            extra = crs_scen - crs_base
            av.append(1000 * av_abs / pop_u15)
            eff.append(100 * av_abs / extra if extra > 0 else np.nan)
        a = stat(av); e = stat(eff)
        print(f"{LABELS[sc]:14s} {a[0]:8.2f} [{a[1]:5.2f},{a[2]:5.2f}]   {e[0]:6.2f} [{e[1]:5.2f},{e[2]:5.2f}]")

    plot(region, d, seeds)


def plot(region, d, seeds):
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 5.6))
    x = np.arange(len(SCENARIOS)); w = 0.26
    for i, b in enumerate(BANDS):
        m, lo, hi = [], [], []
        for sc in SCENARIOS:
            mu, l, h = stat([1000 * d[sc][s]["sev"][b] for s in seeds])
            m.append(mu); lo.append(mu - l); hi.append(h - mu)
        axL.bar(x + (i - 1) * w, m, w, yerr=[lo, hi], capsize=3, color=COLORS[b], label=b)
    axL.set_xticks(x); axL.set_xticklabels([LABELS[s] for s in SCENARIOS], rotation=20, ha="right", fontsize=8.5)
    axL.set_ylabel("severe cases per 1000 children per year")
    axL.set_title("Absolute severe burden (baseline included)")
    axL.legend(title="age band"); axL.grid(axis="y", alpha=0.3)

    scen_p = [s for s in SCENARIOS if s != "baseline"]; xr = np.arange(len(scen_p))
    for i, b in enumerate(BANDS):
        m, lo, hi = [], [], []
        for sc in scen_p:
            red = [100 * (d["baseline"][s]["sev"][b] - d[sc][s]["sev"][b]) / d["baseline"][s]["sev"][b]
                   for s in seeds if d["baseline"][s]["sev"][b] > 0]
            mu, l, h = stat(red); m.append(mu); lo.append(mu - l); hi.append(h - mu)
        axR.bar(xr + (i - 1) * w, m, w, yerr=[lo, hi], capsize=3, color=COLORS[b], label=b)
    axR.axhline(0, color="k", lw=0.8)
    axR.set_xticks(xr); axR.set_xticklabels([LABELS[s] for s in scen_p], rotation=20, ha="right", fontsize=8.5)
    axR.set_ylabel("% reduction in severe incidence vs baseline")
    axR.set_title("Relative effect on severe malaria"); axR.legend(title="age band"); axR.grid(axis="y", alpha=0.3)

    fig.suptitle(f"{region}: projected SMC impact on SEVERE malaria 2023-2027 (mean +/- 95% CI, {len(seeds)} seeds)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = f"data/severe_{region}_panel.png"; fig.savefig(out, dpi=130); print("\nsaved", out)


if __name__ == "__main__":
    report(sys.argv[1])
