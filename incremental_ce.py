"""
Incremental cost-effectiveness analysis (efficiency frontier) across the six
mutually-exclusive SMC scenarios. Orders by cost, removes (strongly & extendedly)
dominated options, computes ICERs between adjacent frontier options, and plots
the cost-effectiveness plane. All region-wide, annual; reuses cost_effect.

    python incremental_ce.py <region>
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 18})

import cost_effect as CE
from cost_effect import (courses, CFR_SEVERE, COST_PER_COURSE, YLL_PER_DEATH,
                         YLD_CLINICAL, YLD_SEVERE, POP_U15, LABELS, BINS)

ORDER = ["baseline", "5cycle", "age10", "5cycle_age10", "age15", "5cycle_age15"]
LAB = dict(LABELS); LAB["baseline"] = "BAU: SMC-4 (U5)"
GDP_PC = 2400


def totals(region):
    """region-wide annual cost and DALYs averted (vs BAU) per scenario."""
    d = CE.load(region)
    seeds = [s for s in CE.SEEDS if all(s in d[sc] for sc in CE.SCENARIOS)]
    pop_u15_model = np.mean([sum(d["baseline"][s]["pop"][b] for b in BINS) for s in seeds])
    scale = POP_U15[region] / pop_u15_model
    out = {"baseline": (0.0, 0.0)}
    for sc in CE.SCENARIOS:
        if sc == "baseline":
            continue
        cl = np.mean([sum((d["baseline"][s]["clin"][k] - d[sc][s]["clin"][k]) * d[sc][s]["pop"][k] for k in BINS) for s in seeds])
        sv = np.mean([sum((d["baseline"][s]["sev"][k] - d[sc][s]["sev"][k]) * d[sc][s]["pop"][k] for k in BINS) for s in seeds])
        crs = np.mean([courses(d[sc][s], sc) - courses(d["baseline"][s], "baseline") for s in seeds])
        daly = (sv * CFR_SEVERE * YLL_PER_DEATH + cl * YLD_CLINICAL + sv * (1 - CFR_SEVERE) * YLD_SEVERE) * scale
        cost = crs * COST_PER_COURSE * scale
        out[sc] = (cost, daly)
    return out


def frontier(pts):
    """pts: {scen:(cost,daly)}. Return frontier scenarios (increasing cost & daly,
    increasing ICER) and mark dominated ones."""
    items = sorted(pts.items(), key=lambda kv: kv[1][0])   # by cost
    status = {}
    kept = []
    for sc, (c, e) in items:
        # strong dominance: costs >= a kept option but averts fewer DALYs
        if kept and e <= kept[-1][1][1]:
            status[sc] = "dominated"
            continue
        kept.append((sc, (c, e)))
    # extended dominance: remove options whose ICER exceeds the next option's ICER
    changed = True
    while changed and len(kept) > 2:
        changed = False
        for i in range(1, len(kept) - 1):
            c0, e0 = kept[i - 1][1]; c1, e1 = kept[i][1]; c2, e2 = kept[i + 1][1]
            icer1 = (c1 - c0) / (e1 - e0); icer2 = (c2 - c1) / (e2 - e1)
            if icer1 > icer2:
                status[kept[i][0]] = "ext-dominated"
                kept.pop(i); changed = True
                break
    for sc, _ in kept:
        status.setdefault(sc, "frontier")
    return status, kept


def report(region):
    pts = totals(region)
    status, kept = frontier(pts)
    print(f"\n=== {region} INCREMENTAL cost-effectiveness (region-wide annual, vs BAU) ===")
    print(f"{'scenario':16s}{'cost/yr $':>12s}{'DALYs averted/yr':>18s}{'ICER $/DALY':>14s}  status")
    prev = None
    for sc, (c, e) in sorted(pts.items(), key=lambda kv: kv[1][0]):
        icer = ""
        if status[sc] == "frontier" and prev is not None:
            icer = f"{(c - prev[0]) / (e - prev[1]):,.0f}"
        if status[sc] == "frontier":
            prev = (c, e)
        print(f"{LAB[sc]:16s}{c:>12,.0f}{e:>18,.0f}{icer:>14s}  {status[sc]}")

    # plot cost-effectiveness plane
    fig, ax = plt.subplots(figsize=(11, 6.5))
    for sc, (c, e) in pts.items():
        col = "#d62728" if status[sc] == "frontier" else "#999999"
        ax.scatter(e, c / 1e6, s=130, color=col, zorder=3)
        ax.annotate(LAB[sc], (e, c / 1e6), textcoords="offset points", xytext=(7, 6), fontsize=12)
    fx = [kv[1][1] for kv in kept]; fy = [kv[1][0] / 1e6 for kv in kept]
    ax.plot(fx, fy, "-", color="#d62728", lw=2.2, zorder=2, label="efficiency frontier")
    # WTP threshold slope lines (0.5x and 1x GDP/capita per DALY)
    emax = max(e for _, e in pts.values())
    for k, ls in [(GDP_PC, "--"), (GDP_PC / 2, ":")]:
        ax.plot([0, emax], [0, k * emax / 1e6], ls, color="grey", lw=1)
        ax.text(emax, k * emax / 1e6, f" ${k}/DALY", color="grey", fontsize=12, va="center")
    ax.set_xlabel("DALYs averted per year (region-wide)"); ax.set_ylabel("SMC cost per year (US$ million)")
    ax.set_title(f"{region.replace('_', ' ').title()} — cost-effectiveness plane & efficiency frontier")
    ax.legend(loc="upper left"); ax.grid(alpha=0.3)
    ax.margins(x=0.12)
    fig.tight_layout(); out = f"data/incremental_ce_{region}.png"; fig.savefig(out, dpi=130); print("\nsaved", out)


if __name__ == "__main__":
    report(sys.argv[1])
