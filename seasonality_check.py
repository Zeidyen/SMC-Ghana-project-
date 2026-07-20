"""
Seasonality validation from the EXISTING BAU projection (no new sims). SMC never
touches the over-5 bands in BAU, so their monthly clinical-incidence SHAPE is a
clean transmission-seasonality signal. Compare the model's over-5 monthly
climatology to the observed routine DHIMS monthly cases (both mean-normalised ->
shape only), per region, with a shape correlation.

    python seasonality_check.py <region>
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

OBS_COL = {"upper_east": "Upper East|pos", "upper_west": "Upper West|pos", "northern": "Northern|pos"}
TITLE = {"upper_east": "Upper East", "northern": "Northern", "upper_west": "Upper West"}
OVER5 = [1, 2]   # 5-10, 10-15 age-bin indices (never SMC-covered in BAU)
MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


def model_climatology(region):
    exp = manifest.latest_proj_exp(region)
    base = pd.Timestamp(f"{H.SIM_START_YEAR}-01-01")
    by_month = {m: [] for m in range(1, 13)}
    for e in os.scandir(exp):
        if not e.is_dir() or e.name == "Assets":
            continue
        t = os.path.join(e.path, "tags.json"); rep = os.path.join(e.path, "output", "MalariaSummaryReport.json")
        if not (os.path.exists(t) and os.path.exists(rep)):
            continue
        if json.load(open(t))["tags"].get("scen") != "baseline":
            continue
        sr = json.load(open(rep))
        clin = np.array(sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"])[:, OVER5].sum(axis=1)
        tt = np.array(sr["DataByTime"]["Time Of Report"][:len(clin)])
        dates = base + pd.to_timedelta(tt, unit="D")
        yr = dates.year
        m = (yr >= 2023) & (yr <= 2027)                   # projection window
        for month, v in zip(dates.month[m], clin[m]):
            by_month[month].append(v)
    prof = np.array([np.mean(by_month[mo]) for mo in range(1, 13)])
    return prof / prof.mean()


def main(region):
    prof = model_climatology(region)
    obs = pd.read_csv("data/routine_malaria_cases_monthly.csv", parse_dates=["date"])
    obs["mo"] = obs["date"].dt.month
    op = obs.groupby("mo")[OBS_COL[region]].mean(); op = (op / op.mean()).reindex(range(1, 13)).values
    corr = np.corrcoef(prof, op)[0, 1]
    print(f"{region}: model over-5 vs routine-cases seasonality  shape corr = {corr:.3f}")

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(1, 13)
    ax.plot(x, prof, "o-", color="#08519c", lw=2.8, ms=9, label="model (over-5 clinical, BAU)")
    ax.plot(x, op, "s--", color="#d62728", lw=2.8, ms=9, label="observed routine cases (DHIMS)")
    ax.set_xticks(x); ax.set_xticklabels(MONTHS)
    ax.set_ylabel("relative seasonal intensity (mean = 1)", fontsize=18)
    ax.set_xlabel("month", fontsize=18)
    ax.set_title(f"{TITLE[region]} — transmission seasonality: model vs routine cases", fontsize=18)
    ax.tick_params(axis="both", labelsize=18)
    ax.legend(fontsize=18, framealpha=0.9); ax.grid(alpha=0.3)
    fig.tight_layout(); out = f"data/seasonality_{region}.png"; fig.savefig(out, dpi=130)
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1])
