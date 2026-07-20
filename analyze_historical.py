"""
Compare a historical run's modeled under-5 PfPR to observed survey PfPR (microscopy),
sampling the model over each survey's field-work window. Also reports annual EIR.

    python analyze_historical.py <region>
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

import manifest
from historical import SIM_START_YEAR

BASE = pd.Timestamp(f"{SIM_START_YEAR}-01-01")


def load_model(region):
    exp = sorted(glob.glob(os.path.join(manifest.job_directory, f"e_ghana_hist_{region}_*")),
                 key=os.path.getmtime)[-1]
    out = next(r for r, _d, fs in os.walk(exp) if "MalariaSummaryReport.json" in fs)
    sr = json.load(open(os.path.join(out, "MalariaSummaryReport.json")))
    u5 = [row[0] for row in sr["DataByTimeAndAgeBins"]["PfPR by Age Bin"]]
    t = sr["DataByTime"]["Time Of Report"][:len(u5)]
    pfpr = pd.Series(u5, index=pd.DatetimeIndex([BASE + pd.Timedelta(days=d) for d in t]))
    eir = pd.Series(sr["DataByTime"]["Annual EIR"][:len(u5)], index=pfpr.index)
    return pfpr, eir


def compare(region):
    pfpr, eir = load_model(region)
    df = pd.read_csv("data/three_region_data.csv", comment="#")
    d = df[df.region == region]
    win = pd.read_csv("data/survey_windows.csv", comment="#")
    rows = []
    for _, r in d.iterrows():
        w = win[win.year == r.year].iloc[0]
        ds = pd.Timestamp(f"{int(r.year)}-01-01") + pd.Timedelta(days=int(w.doy_start))
        de = pd.Timestamp(f"{int(r.year)}-01-01") + pd.Timedelta(days=int(min(w.doy_end, 364)))
        m = pfpr[(pfpr.index >= ds) & (pfpr.index <= de)].mean()
        rows.append(dict(year=int(r.year), obs=r.pfpr_micro, model=m, date=ds + (de - ds) / 2))
    res = pd.DataFrame(rows)
    rmse = np.sqrt(np.mean((res.obs - res.model) ** 2))
    print(f"\n=== {region} : model vs observed under-5 PfPR (survey-window avg) ===")
    print(res[["year", "obs", "model"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"RMSE = {rmse:.3f}")
    ann_eir = eir[eir.index.month == 12].groupby(eir[eir.index.month == 12].index.year).last()
    print(f"model annual EIR range {ann_eir.min():.0f}-{ann_eir.max():.0f}")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(pfpr.index, pfpr.values, color="#1f77b4", lw=1, label="model under-5 PfPR")
    ax.plot(res.date, res.obs, "o", color="#d62728", ms=9, label="observed (microscopy)")
    ax.axvspan(BASE, pd.Timestamp("2011-01-01"), color="grey", alpha=0.12)
    ax.set_ylim(0, 0.8); ax.set_ylabel("Under-5 PfPR"); ax.grid(alpha=0.3); ax.legend()
    ax.set_title(f"{region} historical fit (RMSE={rmse:.3f})")
    fig.tight_layout()
    out = os.path.join("data", f"historical_fit_{region}.png")
    fig.savefig(out, dpi=130); print("saved", out)
    return rmse


if __name__ == "__main__":
    compare(sys.argv[1])
