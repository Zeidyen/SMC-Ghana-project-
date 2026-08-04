# Seasonal Malaria Chemoprevention in Northern Ghana — an EMOD modelling and cost-effectiveness study

Agent-based *Plasmodium falciparum* transmission models (EMOD / [emodpy-malaria](https://github.com/InstituteforDiseaseModeling/emodpy-malaria)) for the three high-burden northern regions of Ghana — **Upper East, Northern, and Upper West** — used to evaluate options for expanding Seasonal Malaria Chemoprevention (SMC): **adding a fifth monthly cycle** and/or **extending age eligibility** from under-5 to 10 or 15 years. Each regional model is independently calibrated to survey prevalence and drives a 2023–2027 projection of clinical incidence, severe malaria, deaths, parasite prevalence, anaemia, and cost-effectiveness.

**[▸ Interactive policy dashboard](https://zeidyen.github.io/SMC-Ghana-project-/)** — pick a region, compare the six scenarios, and vary coverage, cost per course and willingness to pay. Self-contained single page (`index.html`); regenerate with `python build_dashboard.py`.

## Key findings

- All three regional models reproduce observed under-five RDT prevalence over 2011–2022 (best-fit relative transmission intensity 1.8 / 2.0 / 2.5 for Upper East / Northern / Upper West).
- The **same efficiency frontier appears in every region**: only the three five-cycle scenarios are non-dominated — it is never cost-effective to extend the age range without also adding the fifth cycle.
- The fifth cycle is the most cost-effective way to avert **deaths** (concentrated in under-fives); age extension averts the most **clinical cases** (in older children).
- Full package (SMC-5, U15) across the three regions: ~2.5 million clinical cases and ~435 child deaths averted per year, at ~US$4.3 million/year (provider perspective, ~US$135–168 per DALY). From a health-system perspective including averted case-management costs, every scenario is **cost-saving**.

## Scenarios

| Code | Label | Cycles | Age ceiling |
|---|---|---|---|
| `baseline` | BAU: SMC-4 (U5) | 4 | 5 |
| `5cycle` | SMC-5 (U5) | 5 | 5 |
| `age10` | SMC-4 (U10) | 4 | 10 |
| `age15` | SMC-4 (U15) | 4 | 15 |
| `5cycle_age10` | SMC-5 (U10) | 5 | 10 |
| `5cycle_age15` | SMC-5 (U15) | 5 | 15 |

Regions are passed on the command line as `upper_east`, `northern`, or `upper_west`.

## Pipeline

The workflow is a sequence of stages; each regional analysis depends on a completed burn-in and projection.

1. **Climate inputs** — `climate_fetch.py`, `build_weather.py` build the per-region EMOD weather files in `climate/`.
2. **Burn-in** — `burnin.py` runs a 50-year equilibrium to establish transmission (with the `SMCReached` demographic property), then serializes for pickup.
3. **Calibration** — `calibrate_pfpr.py` sweeps the larval-habitat scale (`x_Temporary_Larval_Habitat`) across full burn-ins and fits each region's under-five PfPR to survey data. `calibrate_trajectory.py` / `caltraj_clean.py` produce the calibration trajectory figures.
4. **Projection** — `project.py` runs 2023–2027 for all six scenarios × 60 stochastic seeds off the serialized burn-in.
5. **Analysis & figures** (all read the newest projection via `manifest.py`):
   - `cost_effect.py` — deaths averted, cost per case / severe / death / DALY, CFR sensitivity, health-system cost-offset secondary analysis, one-way sensitivity.
   - `incremental_ce.py` — incremental cost-effectiveness, dominance/extended-dominance, efficiency frontier.
   - `consolidated_fig.py` — four-panel per-region impact + cost-effectiveness summary.
   - `region_compare.py` — cross-region comparison (cost-effectiveness vs transmission, deaths vs population, per-child impact).
   - `timeseries.py`, `annual_plot.py`, `severe.py`, `averted_panel.py` — incidence trajectories and severe/deaths panels.
   - `prev_anemia.py` — parasite-prevalence and childhood-anaemia reductions.
   - `seasonality_check.py` — seasonality validation against routine DHIMS monthly cases.

### Core modules

- `historical.py` — the model definition: demographics, ITN mass campaigns, IRS, case management, and the historical SMC schedule per region.
- `effect_sizes.py` — intervention effect sizes (ITN blocking/killing and waning, IRS killing by insecticide era, SMC projection coverage).
- `region_config.py` — per-region settings; `manifest.py` — experiment/output locations and newest-experiment selection.

## Requirements

- Python 3 with `emodpy-malaria` (v5.2.1), `idmtools` and the idmtools `ContainerPlatform`, plus `numpy`, `pandas`, `matplotlib`.
- Docker (e.g. via OrbStack) to run the EMOD `Eradication` binary in a container.
- The EMOD `Eradication` binary itself is **not** committed (see below); fetch it into `download/` via emodpy.

Create a virtual environment and install emodpy-malaria per the [official instructions](https://docs.idmod.org/projects/emodpy-malaria/en/latest/). Analysis/plotting scripts that read existing outputs only need numpy/pandas/matplotlib.

## Repository layout

```
*.py               model, calibration, projection, analysis and plotting scripts
climate/           per-region EMOD weather inputs + climatology CSVs
data/              input/reference data, calibration curves, projection CSVs, generated figures
docs/              manuscripts (.docx)
manuscript_three_region.md   three-region manuscript (source)
```

### Not tracked (see `.gitignore`)

- `jobs/` — raw EMOD experiment output (~38 GB); regenerate by re-running the pipeline.
- `env/` — local virtual environment.
- `download/` — the EMOD `Eradication` binary (fetch separately).
- `__pycache__/`, logs, OS/Word temp files.

## Reproducing the figures

With a completed projection in `jobs/`, regenerate any figure directly, e.g.:

```bash
python caltraj_clean.py upper_east      # calibration trajectory (Figure 1)
python consolidated_fig.py northern     # impact + cost-effectiveness (Figure 2)
python incremental_ce.py upper_west     # efficiency frontier (Figure 4)
python region_compare.py                # cross-region comparison (Figure 5)
python seasonality_check.py upper_east  # seasonality validation
```

Figures are written to `data/` at 18-pt font for manuscript use.
