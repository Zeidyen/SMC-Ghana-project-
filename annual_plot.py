"""
Year-on-year annual projection plot (2023-2027): annual-average incidence by
scenario and age band, mean + 95% CI. Cleaner than the monthly time-series.

    python annual_plot.py <region> [severe]
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 18})

from export_annual import load, ci, SCENARIOS, LABELS, BANDS, PROJ

# colour = AGE CEILING (light->dark = U5/U10/U15); linestyle = cycles (4=dashed, 5=solid)
COLORS = {"baseline": "#9ecae1", "5cycle": "#9ecae1",       # U5
          "age10": "#4292c6", "5cycle_age10": "#4292c6",    # U10
          "age15": "#084594", "5cycle_age15": "#084594"}    # U15
FOUR_CYCLE = {"baseline", "age10", "age15"}                 # dashed; 5-cycle = solid


def plot(region, metric="clinical"):
    d = load(region)
    seeds = [s for s in range(1, 11) if all(s in d[sc] for sc in SCENARIOS)]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    for ax, b in zip(axes.ravel(), BANDS):
        for sc in SCENARIOS:
            m = [ci([d[sc][s][metric][Y][b] for s in seeds])[0] for Y in PROJ]
            lo = [ci([d[sc][s][metric][Y][b] for s in seeds])[1] for Y in PROJ]
            hi = [ci([d[sc][s][metric][Y][b] for s in seeds])[2] for Y in PROJ]
            lw = 2.8 if sc in ("baseline", "5cycle_age15") else 1.7
            ls = "--" if sc in FOUR_CYCLE else "-"
            ax.plot(PROJ, m, marker="o", ls=ls, color=COLORS[sc], lw=lw, ms=5, label=LABELS[sc])
            if sc in ("baseline", "5cycle_age15"):
                ax.fill_between(PROJ, lo, hi, color=COLORS[sc], alpha=0.15)
        ax.set_title(b); ax.grid(alpha=0.3); ax.set_xticks(PROJ)
        ax.set_ylabel(f"{metric} cases /1000/yr"); ax.set_ylim(bottom=0)
    axes.ravel()[0].legend(fontsize=8, ncol=2, loc="lower left")
    fig.suptitle(f"{region}: annual {metric} incidence 2023-2027 — BAU vs SMC scenarios (2k, 60 seeds, mean +/- 95% CI)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = f"data/annual_{metric}_{region}.png"; fig.savefig(out, dpi=130); print("saved", out)


if __name__ == "__main__":
    region = sys.argv[1]
    plot(region, "severe" if len(sys.argv) > 2 and sys.argv[2] == "severe" else "clinical")
