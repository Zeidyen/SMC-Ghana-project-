"""
Cross-region comparison + inference. Pulls the full-package (SMC-5 U15) impact and
cost-effectiveness for all three regions, tabulates them against transmission
intensity (x) and population, and plots a comparison figure. Reuses cost_effect.

    python region_compare.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 18})

import cost_effect as CE
from cost_effect import (courses, CFR_SEVERE, COST_PER_COURSE, YLL_PER_DEATH,
                         YLD_CLINICAL, YLD_SEVERE, POP_U15, BINS)

REGIONS = ["upper_east", "northern", "upper_west"]
RLAB = {"upper_east": "Upper East", "northern": "Northern", "upper_west": "Upper West"}
XCAL = {"upper_east": 1.789, "northern": 2.0, "upper_west": 2.5}
FULL = "5cycle_age15"


def metrics(region):
    d = CE.load(region)
    seeds = [s for s in CE.SEEDS if all(s in d[sc] for sc in CE.SCENARIOS)]
    pm = np.mean([sum(d["baseline"][s]["pop"][b] for b in BINS) for s in seeds])
    scale = POP_U15[region] / pm
    # per-1000 U15 clinical averted, severe % reduction (U15), deaths/yr, cost/DALY (full package)
    cl = np.mean([sum((d["baseline"][s]["clin"][k] - d[FULL][s]["clin"][k]) for k in BINS) /
                  sum(d[FULL][s]["pop"][k] for k in BINS) * 1000 *
                  sum(d[FULL][s]["pop"][k] for k in BINS) / sum(d[FULL][s]["pop"][k] for k in BINS) for s in seeds])
    # cleaner: pop-weighted clinical averted per 1000 U15
    clin_av = np.mean([sum((d["baseline"][s]["clin"][k] - d[FULL][s]["clin"][k]) * d[FULL][s]["pop"][k] for k in BINS) /
                       sum(d[FULL][s]["pop"][k] for k in BINS) * 1000 for s in seeds])
    bsev = np.array([sum(d["baseline"][s]["sev"][k] * d[FULL][s]["pop"][k] for k in BINS) for s in seeds])
    xsev = np.array([sum(d[FULL][s]["sev"][k] * d[FULL][s]["pop"][k] for k in BINS) for s in seeds])
    sev_red = 100 * (bsev.sum() - xsev.sum()) / bsev.sum()
    deaths = np.mean([sum((d["baseline"][s]["sev"][k] - d[FULL][s]["sev"][k]) * d[FULL][s]["pop"][k]
                          for k in BINS) * CFR_SEVERE for s in seeds]) * scale
    M = np.array([[sum((d["baseline"][s]["clin"][k] - d[FULL][s]["clin"][k]) * d[FULL][s]["pop"][k] for k in BINS),
                   sum((d["baseline"][s]["sev"][k] - d[FULL][s]["sev"][k]) * d[FULL][s]["pop"][k] for k in BINS),
                   courses(d[FULL][s], FULL) - courses(d["baseline"][s], "baseline")] for s in seeds])
    cl_t, sv_t, crs_t = M[:, 0].sum(), M[:, 1].sum(), M[:, 2].sum()
    daly = sv_t * CFR_SEVERE * YLL_PER_DEATH + cl_t * YLD_CLINICAL + sv_t * (1 - CFR_SEVERE) * YLD_SEVERE
    cpd = crs_t * COST_PER_COURSE / daly
    return dict(clin=clin_av, sev=sev_red, deaths=deaths, cpd=cpd, x=XCAL[region], pop=POP_U15[region])


def main():
    m = {r: metrics(r) for r in REGIONS}
    print(f"\n{'region':12s}{'x':>6s}{'U15 pop':>10s}{'clin/1000/yr':>14s}{'severe% ':>9s}{'deaths/yr':>11s}{'$/DALY':>8s}")
    for r in REGIONS:
        z = m[r]
        print(f"{RLAB[r]:12s}{z['x']:>6.2f}{z['pop']:>10,d}{z['clin']:>14.0f}{z['sev']:>9.0f}{z['deaths']:>11.0f}{z['cpd']:>8.0f}")

    fig, ax = plt.subplots(1, 3, figsize=(20, 6))
    cols = ["#9ecae1", "#4292c6", "#084594"]
    xb = np.arange(3)
    # A: cost per DALY vs transmission x  (clean monotonic gradient)
    for i, r in enumerate(REGIONS):
        ax[0].scatter(m[r]["x"], m[r]["cpd"], s=180, color=cols[i])
        ax[0].annotate(RLAB[r], (m[r]["x"], m[r]["cpd"]), textcoords="offset points", xytext=(9, 0), fontsize=15)
    ax[0].set_xlabel("relative transmission intensity"); ax[0].set_ylabel("cost per DALY averted (US$)")
    ax[0].set_title("A. Cost-effectiveness vs transmission"); ax[0].grid(alpha=0.3)
    ax[0].set_ylim(0, 200)
    # B: absolute deaths averted/yr scales with population
    ax[1].bar(xb, [m[r]["deaths"] for r in REGIONS], color=cols)
    for i, r in enumerate(REGIONS):
        ax[1].text(i, m[r]["deaths"], f"{m[r]['deaths']:.0f}\n({m[r]['pop']//1000}k U15)", ha="center", va="bottom", fontsize=14)
    ax[1].set_xticks(xb); ax[1].set_xticklabels([RLAB[r] for r in REGIONS])
    ax[1].set_ylabel("child deaths averted / year"); ax[1].set_title("B. Deaths scale with population"); ax[1].margins(y=0.18)
    # C: per-child clinical impact (high everywhere)
    ax[2].bar(xb, [m[r]["clin"] for r in REGIONS], color=cols)
    for i, r in enumerate(REGIONS):
        ax[2].text(i, m[r]["clin"], f"{m[r]['clin']:.0f}", ha="center", va="bottom", fontsize=15)
    ax[2].set_xticks(xb); ax[2].set_xticklabels([RLAB[r] for r in REGIONS])
    ax[2].set_ylabel("clinical cases averted /1000 U15/yr"); ax[2].set_title("C. Per-child impact"); ax[2].margins(y=0.15)
    fig.suptitle("Cross-region comparison — full package (SMC-5 U15) vs BAU", fontsize=19)
    fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig("data/region_compare.png", dpi=130); print("\nsaved data/region_compare.png")


if __name__ == "__main__":
    main()
