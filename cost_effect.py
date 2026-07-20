"""
Deaths averted + cost-effectiveness layer on the completed projection.
Deaths = severe cases x case-fatality ratio. Cost = additional SMC child-courses
(priced per course) using the ACTUAL literature per-band projection coverage.
Reports, per scenario vs BAU: clinical/severe/deaths averted (per 1000 U15/yr and
scaled to the real regional under-15 population) and cost per case / severe /
death averted. Pooled across seeds with a seed-bootstrap 95% CI (rare-event safe).

    python cost_effect.py <region>
"""
import os
import sys
import glob
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 18})

import numpy as np
import pandas as pd

import manifest
import historical as H

# ---- literature parameters (transparent; adjust here) ----
CFR_SEVERE = 0.10            # severe-malaria case-fatality ratio (sensitivity 0.05-0.20)
CFR_RANGE = [0.05, 0.10, 0.20]
COST_PER_COURSE = 0.90       # USD per child-cycle (ACCESS-SMC ~$3.63/child/yr / 4; Gilmartin 2021 LGH)
# DALY weights (GBD): discounted life-years lost per young-child malaria death, and
# disability-weight x duration per uncomplicated / severe (survivor) episode.
YLL_PER_DEATH = 30.0
YLD_CLINICAL = 0.006
YLD_SEVERE = 0.05
DISCOUNT = 0.03              # annual discount rate on costs and effects (base year 2021 US$)
# Averted case-management costs (health-system perspective secondary analysis).
# Provider unit costs, 2021 US$: outpatient uncomplicated episode (Dx + ACT + visit)
# and severe-malaria inpatient admission (Ghana / sub-Saharan estimates).
COST_OUTPATIENT = 5.0        # per uncomplicated case treated (range 2-8)
COST_SEVERE_INPT = 50.0      # per severe case admitted (range 30-130)
COST_OUTPATIENT_RANGE = [2.0, 5.0, 8.0]
COST_SEVERE_INPT_RANGE = [30.0, 50.0, 130.0]
COST_PER_COURSE_RANGE = [0.45, 0.90, 1.80]
YLL_RANGE = [20.0, 30.0, 35.0]
# real under-15 population by region (region pop x ~40%); ~1.3M Upper East, 0.9M Upper West, 2.3M Northern
POP_U15 = {"upper_east": 520_000, "upper_west": 360_000, "northern": 900_000}

SCENARIOS = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
LABELS = {"5cycle": "SMC-5 (U5)", "age10": "SMC-4 (U10)", "age15": "SMC-4 (U15)",
          "5cycle_age10": "SMC-5 (U10)", "5cycle_age15": "SMC-5 (U15)"}
SEEDS = list(range(1, 61))
BINS = {"U5": 0, "5-10": 1, "10-15": 2}
CYCLES = {"baseline": 4, "5cycle": 5, "age10": 4, "age15": 4, "5cycle_age10": 5, "5cycle_age15": 5}
AGEMAX = {"baseline": 5, "5cycle": 5, "age10": 10, "age15": 15, "5cycle_age10": 10, "5cycle_age15": 15}
# projection per-cycle coverage averaged over 2023-2027 (from ES.SMC_PROJ_COVERAGE ramp)
COV = {"U5": 0.87, "5-10": np.mean([0.75, 0.80, 0.85, 0.85, 0.85]),
       "10-15": np.mean([0.65, 0.70, 0.75, 0.75, 0.75])}
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
        clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])
        sev = np.array(sr["DataByTimeAndAgeBins"]["Annual Severe Incidence by Age Bin"])
        pop = np.array(sr["DataByTimeAndAgeBins"]["Average Population by Age Bin"])
        tt = np.array(sr["DataByTime"]["Time Of Report"][:len(clin)])
        yr = (base + pd.to_timedelta(tt, unit="D")).year
        m = (yr >= PROJ[0]) & (yr <= PROJ[1])
        d[tg["scen"]][int(tg["seed"])] = dict(
            clin={b: clin[m][:, i].mean() for b, i in BINS.items()},
            sev={b: sev[m][:, i].mean() for b, i in BINS.items()},
            pop={b: pop[m][:, i].mean() for b, i in BINS.items()})
    return d


def courses(rec, sc):
    """Annual SMC child-courses delivered under scenario sc for this seed."""
    bands = ["U5"] + (["5-10"] if AGEMAX[sc] >= 10 else []) + (["10-15"] if AGEMAX[sc] >= 15 else [])
    return CYCLES[sc] * sum(rec["pop"][b] * COV[b] for b in bands)


def report(region):
    d = load(region)
    seeds = [s for s in SEEDS if all(s in d[sc] for sc in SCENARIOS)]
    pop_u15_model = np.mean([sum(d["baseline"][s]["pop"][b] for b in BINS) for s in seeds])
    scale = POP_U15[region] / pop_u15_model          # model-agents -> real population
    np.random.seed(0)

    def per_seed(sc, s):
        b, x = d["baseline"][s], d[sc][s]
        cl = sum((b["clin"][k] - x["clin"][k]) * x["pop"][k] for k in BINS)   # clinical cases averted (agents)
        sv = sum((b["sev"][k] - x["sev"][k]) * x["pop"][k] for k in BINS)     # severe averted
        dth = sv * CFR_SEVERE                                                  # deaths averted
        crs = courses(x, sc) - courses(b, "baseline")                         # extra child-courses
        return cl, sv, dth, crs

    def dalys(M, ix, cfr):   # YLL from deaths + YLD from morbidity
        sv = M[ix, 1].sum(); cl = M[ix, 0].sum()
        return sv * cfr * YLL_PER_DEATH + cl * YLD_CLINICAL + sv * (1 - cfr) * YLD_SEVERE

    print(f"\n=== {region} DEATHS AVERTED + COST-EFFECTIVENESS 2023-2027 ===")
    print(f"(CFR_severe={CFR_SEVERE}, ${COST_PER_COURSE}/course, YLL/death={YLL_PER_DEATH}, U15 pop={POP_U15[region]:,}, {len(seeds)} seeds, [95% CI])")
    print(f"\n{'scenario':16s}{'deaths averted/yr':>20s}{'$/case':>9s}{'$/severe':>13s}{'$/death':>16s}{'$/DALY':>15s}")
    res = {}
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        M = np.array([per_seed(sc, s) for s in seeds])   # columns: cl, sv, dth, crs (per agent-pop)

        def boot(f):
            pt = f(np.arange(len(seeds)))
            bs = np.array([f(np.random.randint(0, len(seeds), len(seeds))) for _ in range(2000)])
            bs = bs[np.isfinite(bs)]
            return pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)

        deaths_scaled = boot(lambda ix: M[ix, 2].sum() / len(ix) * scale)     # deaths/yr region-wide
        cost = lambda ix: M[ix, 3].sum() * COST_PER_COURSE
        cpc = boot(lambda ix: cost(ix) / M[ix, 0].sum() if M[ix, 0].sum() > 0 else np.nan)
        cps = boot(lambda ix: cost(ix) / M[ix, 1].sum() if M[ix, 1].sum() > 0 else np.nan)
        cpd = boot(lambda ix: cost(ix) / (M[ix, 1].sum() * CFR_SEVERE) if M[ix, 1].sum() > 0 else np.nan)
        cpdaly = boot(lambda ix: cost(ix) / dalys(M, ix, CFR_SEVERE) if dalys(M, ix, CFR_SEVERE) > 0 else np.nan)
        f = lambda v: f"{v[0]:.0f} [{v[1]:.0f},{v[2]:.0f}]"
        print(f"{LABELS[sc]:16s}{f(deaths_scaled):>20s}{cpc[0]:>9.0f}{cps[0]:>13.0f}{f(cpd):>16s}{f(cpdaly):>15s}")
        res[sc] = dict(deaths=deaths_scaled, cpdaly=cpdaly)
    plot_ce(region, res)

    # CFR sensitivity: deaths averted (region/yr) and $/DALY at CFR 0.05/0.10/0.20
    print(f"\n--- CFR sensitivity: deaths averted/yr  (and $/DALY) ---")
    print(f"{'scenario':16s}" + "".join(f"{'CFR '+str(c):>22s}" for c in CFR_RANGE))
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        M = np.array([per_seed(sc, s) for s in seeds])
        cells = []
        for cfr in CFR_RANGE:
            dth = M[:, 1].mean() * cfr * scale
            cd = M[:, 3].sum() * COST_PER_COURSE / dalys(M, np.arange(len(seeds)), cfr)
            cells.append(f"{dth:.0f} (${cd:.0f})")
        print(f"{LABELS[sc]:16s}" + "".join(f"{c:>22s}" for c in cells))

    # absolute region-wide annual totals for the full package
    print(f"\n--- region-wide annual totals (scaled to {POP_U15[region]:,} under-15) ---")
    print(f"{'scenario':16s}{'clinical averted/yr':>22s}{'severe averted/yr':>20s}{'deaths averted/yr':>20s}{'SMC cost/yr $':>16s}")
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        M = np.array([per_seed(sc, s) for s in seeds]).mean(axis=0)
        print(f"{LABELS[sc]:16s}{M[0]*scale:>22,.0f}{M[1]*scale:>20,.0f}{M[2]*scale:>20,.0f}{M[3]*COST_PER_COURSE*scale:>16,.0f}")

    secondary(region, d, seeds, scale)
    sensitivity(region, d, seeds, scale)


def _M(d, seeds, sc):
    """per-seed matrix [cl, sv, dth, crs] of averted counts vs BAU (agent-pop units)."""
    def per_seed(s):
        b, x = d["baseline"][s], d[sc][s]
        cl = sum((b["clin"][k] - x["clin"][k]) * x["pop"][k] for k in BINS)
        sv = sum((b["sev"][k] - x["sev"][k]) * x["pop"][k] for k in BINS)
        crs = courses(x, sc) - courses(b, "baseline")
        return cl, sv, sv * CFR_SEVERE, crs
    return np.array([per_seed(s) for s in seeds])


def _daly(M, cfr=CFR_SEVERE, yll=YLL_PER_DEATH, ydc=YLD_CLINICAL, yds=YLD_SEVERE):
    sv, cl = M[:, 1].sum(), M[:, 0].sum()
    return sv * cfr * yll + cl * ydc + sv * (1 - cfr) * yds


def secondary(region, d, seeds, scale):
    """Health-system perspective: net cost = SMC delivery cost - averted case-management
    cost (outpatient for clinical, inpatient for severe). Reports net cost/yr and net $/DALY."""
    print(f"\n--- SECONDARY: health-system perspective incl. averted treatment costs "
          f"(outpatient ${COST_OUTPATIENT}/case, inpatient ${COST_SEVERE_INPT}/severe) ---")
    print(f"{'scenario':16s}{'SMC cost/yr $':>15s}{'Tx saved/yr $':>15s}{'net cost/yr $':>16s}{'net $/DALY':>16s}")
    for sc in SCENARIOS:
        if sc == "baseline":
            continue
        M = _M(d, seeds, sc)
        smc = M[:, 3].mean() * COST_PER_COURSE * scale
        saved = (M[:, 0].mean() * COST_OUTPATIENT + M[:, 1].mean() * COST_SEVERE_INPT) * scale
        net = smc - saved
        npd = net / (_daly(M) / len(seeds) * scale) if _daly(M) > 0 else np.nan
        tag = f"{npd:,.0f}" if net > 0 else "COST-SAVING"
        print(f"{LABELS[sc]:16s}{smc:>15,.0f}{saved:>15,.0f}{net:>16,.0f}{tag:>16s}")


def sensitivity(region, d, seeds, scale):
    """One-way sensitivity of the full-package (SMC-5 U15) cost per DALY to each key
    parameter, low/central/high. Provider perspective (base case) unless noted."""
    sc = "5cycle_age15"
    M = _M(d, seeds, sc)
    smc_cost = M[:, 3].sum() * COST_PER_COURSE
    base_cpd = smc_cost / _daly(M)
    print(f"\n--- ONE-WAY SENSITIVITY: full package (SMC-5 U15) cost per DALY, provider perspective ---")
    print(f"base-case $/DALY = {base_cpd:.0f}")
    print(f"{'parameter':22s}{'low':>12s}{'central':>12s}{'high':>12s}")
    rows = [
        ("cost per course $", [M[:, 3].sum() * c / _daly(M) for c in COST_PER_COURSE_RANGE]),
        ("CFR severe", [smc_cost / _daly(M, cfr=c) for c in CFR_RANGE]),
        ("YLL per death", [smc_cost / _daly(M, yll=y) for y in YLL_RANGE]),
        ("YLD clinical wt", [smc_cost / _daly(M, ydc=w) for w in (0.003, 0.006, 0.012)]),
        ("YLD severe wt", [smc_cost / _daly(M, yds=w) for w in (0.025, 0.05, 0.10)]),
    ]
    for name, vals in rows:
        print(f"{name:22s}" + "".join(f"{v:>12.0f}" for v in vals))
    # health-system net $/DALY sensitivity to treatment unit costs
    daly_tot = _daly(M) / len(seeds) * scale
    print(f"{'--- health-system net $/DALY vs treatment unit cost ---':<58s}")
    for label, rng, other in (("outpatient $", COST_OUTPATIENT_RANGE, COST_SEVERE_INPT),
                              ("inpatient(severe) $", COST_SEVERE_INPT_RANGE, COST_OUTPATIENT)):
        vals = []
        for c in rng:
            op, ip = (c, other) if label.startswith("out") else (other, c)
            saved = (M[:, 0].mean() * op + M[:, 1].mean() * ip) * scale
            net = M[:, 3].mean() * COST_PER_COURSE * scale - saved
            vals.append(f"{net/daly_tot:,.0f}" if net > 0 else "COST-SAVING")
        print(f"{label:22s}" + "".join(f"{v:>12s}" for v in vals))


GDP_PC = 2400   # Ghana GDP per capita (~USD); cost-effectiveness threshold reference


def plot_ce(region, res):
    scen = [s for s in SCENARIOS if s != "baseline"]
    # colour = age ceiling: U5 light, U10 mid, U15 dark  [order: 5cyc-U5, U10, U15, 5cyc-U10, 5cyc-U15]
    colors = ["#9ecae1", "#4292c6", "#084594", "#4292c6", "#084594"]
    x = np.arange(len(scen))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2))

    # deaths averted / yr
    m = [res[s]["deaths"][0] for s in scen]
    lo = [res[s]["deaths"][0] - res[s]["deaths"][1] for s in scen]
    hi = [res[s]["deaths"][2] - res[s]["deaths"][0] for s in scen]
    a1.bar(x, m, yerr=[lo, hi], capsize=4, color=colors)
    a1.set_xticks(x); a1.set_xticklabels([LABELS[s] for s in scen], rotation=20, ha="right", fontsize=9)
    a1.set_ylabel("child deaths averted per year"); a1.set_title(f"Deaths averted (region-wide, {POP_U15[region]:,} under-15)")

    # cost per DALY with threshold lines
    m = [res[s]["cpdaly"][0] for s in scen]
    lo = [res[s]["cpdaly"][0] - res[s]["cpdaly"][1] for s in scen]
    hi = [res[s]["cpdaly"][2] - res[s]["cpdaly"][0] for s in scen]
    a2.bar(x, m, yerr=[lo, hi], capsize=4, color=colors)
    a2.axhline(GDP_PC, ls="--", color="grey"); a2.text(len(scen) - 0.5, GDP_PC, " GDP/capita", color="grey", va="bottom", ha="right", fontsize=8)
    a2.axhline(GDP_PC / 2, ls=":", color="grey"); a2.text(len(scen) - 0.5, GDP_PC / 2, " 0.5x GDP/capita", color="grey", va="bottom", ha="right", fontsize=8)
    a2.set_xticks(x); a2.set_xticklabels([LABELS[s] for s in scen], rotation=20, ha="right", fontsize=9)
    a2.set_ylabel("cost per DALY averted (USD)"); a2.set_title("Cost-effectiveness (lower = better; all << threshold)")

    fig.suptitle(f"{region}: mortality impact & cost-effectiveness of SMC scenarios 2023-2027 "
                 f"(CFR {CFR_SEVERE}, ${COST_PER_COURSE}/course, 60 seeds, 95% CI)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = f"data/cost_effect_{region}.png"; fig.savefig(out, dpi=130); print(f"\nsaved {out}")


if __name__ == "__main__":
    report(sys.argv[1])
