"""
Two-panel severe / deaths figure in the projection_panel style:
  (left)  absolute burden per 1000/yr by age band, baseline included
  (right) % reduction vs BAU by age band (pooled across seeds, seed-bootstrap CI,
          the rare-event-appropriate estimator)
Deaths = severe cases x CFR, so the % reduction panel is shared with severe.

    python averted_panel.py <region> <severe|deaths>
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 18})

import cost_effect as CE
from cost_effect import CFR_SEVERE, BINS, LABELS

SCEN = ["baseline", "5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
SLAB = dict(LABELS); SLAB["baseline"] = "BAU: SMC-4 (U5)"
BANDS = {"U5": "U5", "5-10": "5-10", "10-15": "10-15"}
BCOL = {"U5": "#d62728", "5-10": "#1f77b4", "10-15": "#2ca02c"}
RLAB = {"upper_east": "upper_east", "northern": "northern", "upper_west": "upper_west"}


def panel(region, metric):
    d = CE.load(region)
    seeds = [s for s in CE.SEEDS if all(s in d[sc] for sc in SCEN)]
    mult = CFR_SEVERE if metric == "deaths" else 1.0
    unit = "child deaths" if metric == "deaths" else "severe cases"
    np.random.seed(0)

    def rate(sc, s, b):     # per-1000/yr burden for a band
        return d[sc][s]["sev"][b] * mult * 1000

    fig, (aL, aR) = plt.subplots(1, 2, figsize=(15, 5.6))
    x = np.arange(len(SCEN)); w = 0.26

    # LEFT: absolute burden by age band (baseline included)
    for i, b in enumerate(BANDS):
        m, lo, hi = [], [], []
        for sc in SCEN:
            v = np.array([rate(sc, s, b) for s in seeds])
            m.append(v.mean()); lo.append(v.mean() - np.percentile(v, 2.5)); hi.append(np.percentile(v, 97.5) - v.mean())
        aL.bar(x + (i - 1) * w, m, w, yerr=[lo, hi], capsize=2.5, color=BCOL[b], label=b)
    aL.set_xticks(x); aL.set_xticklabels([SLAB[s] for s in SCEN], rotation=20, ha="right", fontsize=8)
    aL.set_ylabel(f"{unit} per 1000 children per year")
    aL.set_title(f"Absolute {unit} by age band (baseline included)"); aL.legend(title="age band")

    # RIGHT: % reduction vs BAU (pooled + seed-bootstrap)
    scen = [s for s in SCEN if s != "baseline"]; xr = np.arange(len(scen))
    for i, b in enumerate(BANDS):
        m, lo, hi = [], [], []
        for sc in scen:
            bc = np.array([d["baseline"][s]["sev"][b] * d[sc][s]["pop"][b] for s in seeds])
            xc = np.array([d[sc][s]["sev"][b] * d[sc][s]["pop"][b] for s in seeds])
            f = lambda ix: 100 * (bc[ix].sum() - xc[ix].sum()) / bc[ix].sum() if bc[ix].sum() > 0 else np.nan
            pt = f(np.arange(len(seeds)))
            bs = np.array([f(np.random.randint(0, len(seeds), len(seeds))) for _ in range(2000)]); bs = bs[np.isfinite(bs)]
            l, h = (np.percentile(bs, 2.5), np.percentile(bs, 97.5)) if len(bs) else (pt, pt)
            m.append(pt); lo.append(pt - l); hi.append(h - pt)
        aR.bar(xr + (i - 1) * w, m, w, yerr=[lo, hi], capsize=2.5, color=BCOL[b], label=b)
    aR.axhline(0, color="k", lw=0.8)
    aR.set_xticks(xr); aR.set_xticklabels([SLAB[s] for s in scen], rotation=20, ha="right", fontsize=8)
    aR.set_ylabel(f"% reduction in {unit} vs BAU"); aR.set_title(f"Relative effect on {unit}"); aR.legend(title="age band")

    fig.suptitle(f"{RLAB[region]}: projected {unit} impact 2023-2027 (mean +/- 95% CI, {len(seeds)} seeds)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = f"data/{metric}_panel_{region}.png"; fig.savefig(out, dpi=130); print("saved", out)


if __name__ == "__main__":
    panel(sys.argv[1], sys.argv[2])
