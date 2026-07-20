"""
Diagnostic plots for the 50-year burn-in.

Figure 1 (equilibration): under-5 PfPR by year, annual EIR by year, population
   over time (vital dynamics), and age-stratified PfPR at equilibrium.
Figure 2 (equilibrium seasonality): last 4 years of daily rainfall / EIR / prevalence.

Usage: python burnin_plots.py [experiment_dir]
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


def find_exp(arg=None):
    if arg:
        return arg
    exps = sorted(glob.glob(os.path.join(manifest.job_directory, "e_ghana_burnin_50yr_*")),
                  key=os.path.getmtime, reverse=True)
    if not exps:
        raise SystemExit("No 50-year burn-in experiment found.")
    return exps[0]


def load(exp_dir):
    out = next(os.path.join(r) for r, _d, fs in os.walk(exp_dir)
               if "MalariaSummaryReport.json" in fs)
    sr = json.load(open(os.path.join(out, "MalariaSummaryReport.json")))
    ic = json.load(open(os.path.join(out, "InsetChart.json")))
    return sr, ic


def fig_equilibration(sr, ic, path):
    years = np.arange(1, len(sr["DataByTime"]["Annual EIR"]) + 1)
    eir = sr["DataByTime"]["Annual EIR"]
    pfpr_by_age = np.array(sr["DataByTimeAndAgeBins"]["PfPR by Age Bin"])   # [year, agebin]
    u5 = pfpr_by_age[:, 0]
    pfpr_2to10 = sr["DataByTime"]["PfPR_2to10"]

    # population over time from InsetChart
    start = ic["Header"]["Start_Time"]; step = ic["Header"]["Simulation_Timestep"]
    pop = np.array(ic["Channels"]["Statistical Population"]["Data"])
    day = start + np.arange(len(pop)) * step

    # equilibrium age profile = mean of last 5 yearly reports
    age_edges = sr["Metadata"]["Age Bins"]
    labels, lo = [], 0
    for hi in age_edges:
        labels.append(f"{lo}-{hi}" if hi < 125 else f"{lo}+"); lo = hi
    eq_age_pfpr = pfpr_by_age[-5:].mean(axis=0)

    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    ax[0, 0].plot(years, u5, "o-", color="#d62728", label="under-5")
    ax[0, 0].plot(years, pfpr_2to10, "s-", color="#ff7f0e", ms=3, label="2-10 yr")
    ax[0, 0].set_title("PfPR by year (equilibration)"); ax[0, 0].set_xlabel("Burn-in year")
    ax[0, 0].set_ylabel("PfPR"); ax[0, 0].set_ylim(0, 1); ax[0, 0].legend(); ax[0, 0].grid(alpha=0.3)

    ax[0, 1].plot(years, eir, "o-", color="#1f77b4")
    ax[0, 1].set_title("Annual EIR by year"); ax[0, 1].set_xlabel("Burn-in year")
    ax[0, 1].set_ylabel("Infectious bites / person / year"); ax[0, 1].grid(alpha=0.3)

    ax[1, 0].plot(day / 365.0, pop, color="#2ca02c")
    ax[1, 0].set_title("Population over time (vital dynamics)"); ax[1, 0].set_xlabel("Burn-in year")
    ax[1, 0].set_ylabel("Statistical population"); ax[1, 0].grid(alpha=0.3)

    ax[1, 1].bar(labels, eq_age_pfpr * 100, color="#9467bd")
    ax[1, 1].set_title("Equilibrium PfPR by age (mean of last 5 yr)")
    ax[1, 1].set_xlabel("Age band (years)"); ax[1, 1].set_ylabel("PfPR (%)")
    ax[1, 1].tick_params(axis="x", rotation=45); ax[1, 1].grid(axis="y", alpha=0.3)

    fig.suptitle("Navrongo 50-year burn-in — equilibration diagnostics", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("Saved:", path)


def fig_seasonality(ic, path, years_to_show=4):
    start = ic["Header"]["Start_Time"]; step = ic["Header"]["Simulation_Timestep"]
    n = ic["Header"]["Timesteps"]
    day = start + np.arange(n) * step
    mask = day >= (day.max() - years_to_show * 365)
    d = day[mask]

    fig, ax = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    ax[0].plot(d / 365.0, np.array(ic["Channels"]["Rainfall"]["Data"])[mask], color="#1f77b4")
    ax[0].set_ylabel("Rainfall\n(mm/day)")
    ax[1].plot(d / 365.0, np.array(ic["Channels"]["Daily EIR"]["Data"])[mask], color="#ff7f0e")
    ax[1].set_ylabel("Daily EIR\n(inf.bites/day)")
    ax[2].plot(d / 365.0, np.array(ic["Channels"]["True Prevalence"]["Data"])[mask] * 100, color="#d62728")
    ax[2].set_ylabel("True\nprevalence (%)"); ax[2].set_xlabel("Burn-in year")
    for a in ax:
        a.grid(alpha=0.3)
    ax[0].set_title(f"Equilibrium seasonal cycle (last {years_to_show} years of burn-in)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("Saved:", path)


def main():
    exp_dir = find_exp(sys.argv[1] if len(sys.argv) > 1 else None)
    print("Experiment:", exp_dir)
    sr, ic = load(exp_dir)
    here = os.path.dirname(__file__)
    fig_equilibration(sr, ic, os.path.join(here, "burnin_equilibration.png"))
    fig_seasonality(ic, os.path.join(here, "burnin_seasonality.png"))


if __name__ == "__main__":
    main()
