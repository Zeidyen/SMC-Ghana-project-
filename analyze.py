"""
Analyze EMOD malaria outputs (InsetChart.json + MalariaSummaryReport.json).

Demonstrates the three things you'll do constantly:
  1. InsetChart  -> pandas time series -> seasonal dynamics plot + CSV
  2. MalariaSummaryReport DataByTime -> annual EIR / PfPR_2to10 table
  3. MalariaSummaryReport age bins   -> final-year PfPR & clinical incidence by age

Usage:
    python analyze.py                       # uses newest e_eir_validation_* experiment
    python analyze.py <path-to-sim-output-dir>
"""
import os
import sys
import json
import glob

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import manifest


def find_output_dir(arg=None):
    """Resolve a simulation output/ directory (default: newest validation experiment)."""
    if arg:
        return arg
    exps = sorted(glob.glob(os.path.join(manifest.job_directory, "e_eir_validation_*")),
                  key=os.path.getmtime, reverse=True)
    if not exps:
        raise SystemExit("No e_eir_validation_* experiment found — pass a sim output dir.")
    hits = glob.glob(os.path.join(exps[0], "*", "output"))
    if not hits:
        raise SystemExit(f"No output/ dir under {exps[0]}")
    return hits[0]


# ---- 1. InsetChart -> DataFrame ---------------------------------------------
def inset_to_dataframe(output_dir):
    """Load InsetChart.json into a tidy DataFrame indexed by simulation day."""
    ic = json.load(open(os.path.join(output_dir, "InsetChart.json")))
    start = ic["Header"]["Start_Time"]
    step = ic["Header"]["Simulation_Timestep"]
    n = ic["Header"]["Timesteps"]
    day = start + np.arange(n) * step
    df = pd.DataFrame({name: ch["Data"] for name, ch in ic["Channels"].items()})
    df.insert(0, "day", day)
    return df


def plot_seasonal_dynamics(df, path):
    """Four-panel view of the seasonal transmission cycle."""
    fig, axes = plt.subplots(4, 1, figsize=(9, 9), sharex=True)
    axes[0].plot(df["day"], df["Rainfall"], color="#1f77b4")
    axes[0].set_ylabel("Rainfall\n(mm/day)")
    axes[1].plot(df["day"], df["Adult Vectors"], color="#2ca02c")
    axes[1].set_ylabel("Adult\nvectors")
    axes[2].plot(df["day"], df["Daily EIR"], color="#ff7f0e")
    axes[2].set_ylabel("Daily EIR\n(inf. bites/day)")
    axes[3].plot(df["day"], df["True Prevalence"] * 100, color="#d62728")
    axes[3].set_ylabel("True\nprevalence (%)")
    axes[3].set_xlabel("Simulation day")
    for ax in axes:
        ax.grid(alpha=0.3)
        for yr in range(365, int(df["day"].max()) + 1, 365):   # mark year boundaries
            ax.axvline(yr, color="grey", ls=":", alpha=0.5)
    axes[0].set_title("Seasonal malaria dynamics (rainfall -> vectors -> EIR -> prevalence)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("Saved:", path)


# ---- 2 & 3. MalariaSummaryReport --------------------------------------------
def summarize_report(output_dir):
    """Print the annual DataByTime table and return the parsed report."""
    sr = json.load(open(os.path.join(output_dir, "MalariaSummaryReport.json")))
    dbt = sr["DataByTime"]
    tbl = pd.DataFrame({
        "report_day": dbt["Time Of Report"],
        "Annual EIR": dbt["Annual EIR"],
        "PfPR_2to10": dbt["PfPR_2to10"],
    })
    print("\n=== MalariaSummaryReport: DataByTime (per reporting period) ===")
    print(tbl.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return sr


def plot_pfpr_by_age(sr, path):
    """Final-year PfPR and clinical incidence by age bin."""
    age_edges = sr["Metadata"]["Age Bins"]                     # upper edges, e.g. [10,20,...,1000]
    labels = []
    lo = 0
    for hi in age_edges:
        labels.append(f"{lo}-{hi}" if hi < 1000 else f"{lo}+")
        lo = hi
    # DataByTimeAndAgeBins[metric] = list per report of list per age bin. Use last full report.
    pfpr = sr["DataByTimeAndAgeBins"]["PfPR by Age Bin"][-2]
    clin = sr["DataByTimeAndAgeBins"]["Annual Clinical Incidence by Age Bin"][-2]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.5))
    a1.bar(labels, np.array(pfpr) * 100, color="#d62728")
    a1.set_ylabel("PfPR (%)"); a1.set_title("Parasite prevalence by age"); a1.tick_params(axis="x", rotation=45)
    a2.bar(labels, clin, color="#1f77b4")
    a2.set_ylabel("Clinical cases / person / year"); a2.set_title("Clinical incidence by age"); a2.tick_params(axis="x", rotation=45)
    for ax in (a1, a2):
        ax.set_xlabel("Age band (years)"); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("Saved:", path)


def main():
    out = find_output_dir(sys.argv[1] if len(sys.argv) > 1 else None)
    print("Analyzing:", out)

    df = inset_to_dataframe(out)
    print("\n=== InsetChart summary (peak vs trough of each channel) ===")
    for ch in ["Statistical Population", "Adult Vectors", "Daily EIR", "True Prevalence", "New Clinical Cases"]:
        print(f"  {ch:24s} min={df[ch].min():.4g}  max={df[ch].max():.4g}  mean={df[ch].mean():.4g}")
    csv_path = os.path.join(os.path.dirname(__file__), "inset_timeseries.csv")
    df.to_csv(csv_path, index=False)
    print("Wrote full time series ->", csv_path)

    plot_seasonal_dynamics(df, os.path.join(os.path.dirname(__file__), "seasonal_dynamics.png"))
    sr = summarize_report(out)
    plot_pfpr_by_age(sr, os.path.join(os.path.dirname(__file__), "pfpr_by_age.png"))


if __name__ == "__main__":
    main()
