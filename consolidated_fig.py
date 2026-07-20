"""
Consolidated manuscript results figure (2x2) for a region, from the completed
projection. Tells the full story:
  (A) clinical % reduction vs BAU by age band
  (B) severe % reduction vs BAU by age band
  (C) child deaths averted per year (region-wide)
  (D) cost per DALY averted (vs cost-effectiveness thresholds)
Pooled across seeds with seed-bootstrap 95% CIs. Reuses cost_effect for params.

    python consolidated_fig.py <region>
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

BANDS = ["U5", "5-10", "10-15"]
BCOLORS = {"U5": "#d62728", "5-10": "#1f77b4", "10-15": "#2ca02c"}
# colour = age ceiling: U5 light, U10 mid, U15 dark  [order: 5cyc-U5, U10, U15, 5cyc-U10, 5cyc-U15]
SCOLORS = ["#9ecae1", "#4292c6", "#084594", "#4292c6", "#084594"]
GDP_PC = 2400


def boot_ci(f, n, nboot=2000):
    pt = f(np.arange(n))
    bs = np.array([f(np.random.randint(0, n, n)) for _ in range(nboot)])
    bs = bs[np.isfinite(bs)]
    return pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def pooled_pct(d, sc, band, seeds, metric):
    b = np.array([d["baseline"][s][metric][band] * d["baseline"][s]["pop"][band] for s in seeds])
    x = np.array([d[sc][s][metric][band] * d[sc][s]["pop"][band] for s in seeds])
    return boot_ci(lambda ix: 100 * (b[ix].sum() - x[ix].sum()) / b[ix].sum() if b[ix].sum() > 0 else np.nan, len(seeds))


def main(region):
    d = CE.load(region)
    seeds = [s for s in CE.SEEDS if all(s in d[sc] for sc in CE.SCENARIOS)]
    scen = [s for s in CE.SCENARIOS if s != "baseline"]
    pop_u15_model = np.mean([sum(d["baseline"][s]["pop"][b] for b in BINS) for s in seeds])
    scale = POP_U15[region] / pop_u15_model
    np.random.seed(0)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    (A, B), (C, D) = axes
    xw = np.arange(len(scen)); w = 0.26

    # A + B: % reduction by age band (clinical, severe)
    for ax, metric, title in [(A, "clin", "A. Clinical incidence reduction vs BAU"),
                              (B, "sev", "B. Severe malaria reduction vs BAU")]:
        for i, band in enumerate(BANDS):
            m, lo, hi = [], [], []
            for sc in scen:
                pt, l, h = pooled_pct(d, sc, band, seeds, metric)
                m.append(pt); lo.append(pt - l); hi.append(h - pt)
            ax.bar(xw + (i - 1) * w, m, w, yerr=[lo, hi], capsize=2.5, color=BCOLORS[band], label=band)
        ax.axhline(0, color="k", lw=0.8); ax.set_xticks(xw)
        ax.set_xticklabels([LABELS[s] for s in scen], rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("% reduction vs BAU"); ax.set_title(title); ax.legend(title="age band", fontsize=8)

    # C: deaths averted / yr
    md, lod, hid = [], [], []
    for sc in scen:
        dth = np.array([sum((d["baseline"][s]["sev"][k] - d[sc][s]["sev"][k]) * d[sc][s]["pop"][k]
                            for k in BINS) * CFR_SEVERE for s in seeds])
        pt, l, h = boot_ci(lambda ix: dth[ix].sum() / len(ix) * scale, len(seeds))
        md.append(pt); lod.append(pt - l); hid.append(h - pt)
    C.bar(xw, md, yerr=[lod, hid], capsize=4, color=SCOLORS)
    C.set_xticks(xw); C.set_xticklabels([LABELS[s] for s in scen], rotation=20, ha="right", fontsize=8)
    C.set_ylabel("child deaths averted / year"); C.set_title(f"C. Deaths averted (region-wide, {POP_U15[region]:,} U15)")

    # D: cost per DALY
    md, lod, hid = [], [], []
    for sc in scen:
        M = np.array([[sum((d["baseline"][s]["clin"][k] - d[sc][s]["clin"][k]) * d[sc][s]["pop"][k] for k in BINS),
                       sum((d["baseline"][s]["sev"][k] - d[sc][s]["sev"][k]) * d[sc][s]["pop"][k] for k in BINS),
                       courses(d[sc][s], sc) - courses(d["baseline"][s], "baseline")] for s in seeds])

        def cpd(ix):
            cl, sv, crs = M[ix, 0].sum(), M[ix, 1].sum(), M[ix, 2].sum()
            daly = sv * CFR_SEVERE * YLL_PER_DEATH + cl * YLD_CLINICAL + sv * (1 - CFR_SEVERE) * YLD_SEVERE
            return crs * COST_PER_COURSE / daly if daly > 0 else np.nan
        pt, l, h = boot_ci(cpd, len(seeds))
        md.append(pt); lod.append(pt - l); hid.append(h - pt)
    D.bar(xw, md, yerr=[lod, hid], capsize=4, color=SCOLORS)
    D.axhline(GDP_PC, ls="--", color="grey"); D.text(len(scen) - 0.5, GDP_PC, " GDP/capita", color="grey", ha="right", va="bottom", fontsize=8)
    D.axhline(GDP_PC / 2, ls=":", color="grey"); D.text(len(scen) - 0.5, GDP_PC / 2, " 0.5x GDP/capita", color="grey", ha="right", va="bottom", fontsize=8)
    D.set_xticks(xw); D.set_xticklabels([LABELS[s] for s in scen], rotation=20, ha="right", fontsize=8)
    D.set_ylabel("cost per DALY averted (USD)"); D.set_title("D. Cost-effectiveness (all << threshold)")

    fig.suptitle(f"{region}: projected impact & cost-effectiveness of SMC scenarios 2023-2027 "
                 f"(2k, 60 seeds, 95% CI; CFR {CFR_SEVERE}, ${COST_PER_COURSE}/course)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = f"data/consolidated_{region}.png"; fig.savefig(out, dpi=135); print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1])
