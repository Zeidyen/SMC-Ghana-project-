"""Assemble the ENTIRE SMC analysis into one JSON for the policy dashboard:
per region x scenario — clinical-incidence % reduction by age band (impact),
region-wide clinical/severe/deaths averted per year and SMC cost (burden),
cost per DALY and efficiency-frontier status (value-for-money)."""
import json
import numpy as np
import pandas as pd
import cost_effect as CE
from cost_effect import BINS, courses, POP_U15, GDP_PC
import incremental_ce as INC

REGIONS = ["upper_east", "upper_west", "northern"]
# projection CSVs use two naming conventions across regions — support both
SMAP = {"+5th cycle": "5cycle", "age_to_10y": "age10", "age_to_15y": "age15",
        "5th+to10y": "5cycle_age10", "5th+to15y": "5cycle_age15",
        "SMC-5 (U5)": "5cycle", "SMC-4 (U10)": "age10", "SMC-4 (U15)": "age15",
        "SMC-5 (U10)": "5cycle_age10", "SMC-5 (U15)": "5cycle_age15"}
SCEN = ["5cycle", "age10", "age15", "5cycle_age10", "5cycle_age15"]
PROJ = (2023, 2027)

out = {"regions": {}, "labels": CE.LABELS, "pop_u15": POP_U15,
       "gdp": GDP_PC, "wtp_half": GDP_PC / 2,
       "params": {"cost_per_course": CE.COST_PER_COURSE, "cfr": CE.CFR_SEVERE,
                  "yll": CE.YLL_PER_DEATH, "cost_out": CE.COST_OUTPATIENT,
                  "cost_sev": CE.COST_SEVERE_INPT}}

def impact(region):
    df = pd.read_csv(f"data/projection_annual_{region}.csv")
    df = df[(df.metric == "clinical") & df.year.between(*PROJ)]
    df["key"] = df.scenario.map(SMAP)
    res = {}
    for key in SCEN:
        sub = df[df.key == key]
        row = {}
        for ab in ["U5", "5-10", "U15"]:
            v = sub[sub.age_band == ab].pct_reduction_vs_BAU.mean()
            row[ab] = round(float(v), 1) if v == v else None   # NaN -> None
        res[key] = row
    return res

for region in REGIONS:
    d = CE.load(region)
    seeds = [s for s in CE.SEEDS if all(s in d[sc] for sc in CE.SCENARIOS)]
    pop_model = np.mean([sum(d["baseline"][s]["pop"][b] for b in BINS) for s in seeds])
    scale = POP_U15[region] / pop_model
    imp = impact(region)

    # efficiency-frontier status
    pts = INC.totals(region); status, _ = INC.frontier(pts)

    rec = {}
    for sc in SCEN:
        def ps(s):
            b, x = d["baseline"][s], d[sc][s]
            cl = sum((b["clin"][k] - x["clin"][k]) * x["pop"][k] for k in BINS)
            sv = sum((b["sev"][k] - x["sev"][k]) * x["pop"][k] for k in BINS)
            crs = courses(x, sc) - courses(b, "baseline")
            return cl, sv, crs
        M = np.array([ps(s) for s in seeds])
        clin = M[:, 0].mean() * scale; sev = M[:, 1].mean() * scale
        deaths = sev * CE.CFR_SEVERE
        cost = M[:, 2].mean() * CE.COST_PER_COURSE * scale
        daly = (sev * CE.CFR_SEVERE * CE.YLL_PER_DEATH + clin * CE.YLD_CLINICAL
                + sev * (1 - CE.CFR_SEVERE) * CE.YLD_SEVERE)
        tx_saved = clin * CE.COST_OUTPATIENT + sev * CE.COST_SEVERE_INPT
        rec[sc] = {
            "impact": imp[sc],
            "clin_averted": round(clin), "sev_averted": round(sev),
            "deaths_averted": round(deaths), "cost": round(cost),
            "dalys": round(daly), "usd_per_daly": round(cost / daly) if daly > 0 else None,
            "net_cost": round(cost - tx_saved), "cost_saving": bool(cost - tx_saved < 0),
            "frontier": status.get(sc, "?"),
            # for live recompute: region-wide averted counts + extra courses
            "counts": {"clin": round(clin), "sev": round(sev),
                       "courses": round(M[:, 2].mean() * scale)}}
    out["regions"][region] = rec
    print(region, "done")

json.dump(out, open("data/policy_dashboard_data.json", "w"), indent=1)
print("wrote data/policy_dashboard_data.json")
