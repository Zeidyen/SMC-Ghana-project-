"""
Clean RDT-calibration trajectory plot (matches caltraj_upper_east_clean.png style):
monthly under-5 RDT (HRP2) prevalence for every candidate transmission scale x
(light red), the calibrated best-fit x (deep red), and the observed survey points
(black). Reads the region's newest calibration-trajectory experiment.

    python caltraj_clean.py <region>
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

BEST_X = {"upper_east": 1.789, "northern": 2.0, "upper_west": 2.5}
TITLE = {"upper_east": "Upper East", "northern": "Northern", "upper_west": "Upper West"}


def main(region):
    best = BEST_X[region]
    df = pd.read_csv("data/three_region_data.csv", comment="#")
    obs = df[df.region == region].set_index("year")["pfpr_rdt"].dropna()

    exps = glob.glob(os.path.join(manifest.job_directory, f"e_ghana_caltraj_{region}_*"))
    exp = max(exps, key=lambda e: max([os.path.getmtime(p) for p in
              glob.glob(os.path.join(e, "*", "output", "MalariaSummaryReport.json"))] or [0]))
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")

    curves = {}   # x -> (yearfrac, rdt)
    for s in os.scandir(exp):
        if not s.is_dir() or s.name == "Assets":
            continue
        t = os.path.join(s.path, "tags.json"); rep = os.path.join(s.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        x = float(json.load(open(t))["tags"]["x"]); sr = json.load(open(rep))
        rdt = np.array(sr["DataByTimeAndAgeBins"]["PfPR by Age Bin-HRP2"])[:, 0]
        tt = np.array(sr["DataByTime"]["Time Of Report"][:len(rdt)])
        yf = (base + pd.to_timedelta(tt, unit="D"))
        curves[round(x, 3)] = (yf.year + (yf.dayofyear - 1) / 365.25, rdt)

    xk = min(curves, key=lambda k: abs(k - best))     # candidate closest to the projection x
    yfb, rdtb = curves[xk]

    fig, ax = plt.subplots(figsize=(14, 6.4))
    for x, (yf, rdt) in curves.items():
        if x == xk:
            continue
        ax.plot(yf, rdt, color="#f4a6a6", lw=0.8, alpha=0.5, zorder=1)
    ax.plot([], [], color="#f4a6a6", lw=2.5, label=f"simulated (relative transmission intensity {min(curves):g}–{max(curves):g})")
    ax.plot(yfb, rdtb, color="#8b0000", lw=2.6, zorder=3, label=f"best-fit relative transmission intensity = {xk:g}")
    ax.scatter(obs.index + 0.75, obs.values, s=140, color="black", zorder=5, label="observed RDT (surveys)")

    ax.set_xlim(H.SIM_START_YEAR, 2023)
    ax.set_ylim(0, min(1.0, max(0.85, obs.max() + 0.1)))
    ax.set_ylabel("under-5 RDT prevalence", fontsize=18)
    ax.set_xlabel("year", fontsize=18)
    ax.set_title(f"{TITLE[region]} — under-5 RDT calibration, 2011–2022", fontsize=18)
    ax.tick_params(axis="both", labelsize=18)
    ax.legend(loc="upper right", fontsize=18, framealpha=0.9); ax.grid(alpha=0.3)
    fig.tight_layout()
    out = f"data/caltraj_{region}_clean.png"; fig.savefig(out, dpi=130); print("saved", out, f"(best x={xk})")


if __name__ == "__main__":
    main(sys.argv[1])
