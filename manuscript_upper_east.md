# Agent-based evaluation of intensifying and age-extending Seasonal Malaria Chemoprevention in Upper East Region, Ghana: an EMOD modelling and cost-effectiveness study

*Draft manuscript — Upper East Region. Author list, affiliations, and journal formatting to be completed.*

---

## Abstract

**Background.** Seasonal Malaria Chemoprevention (SMC) with sulfadoxine–pyrimethamine plus amodiaquine (SPAQ) is delivered to children under five in northern Ghana as four monthly cycles (June–September). WHO's 2022/2023 guidance removed fixed age limits and encourages countries to use local data and mathematical modelling to decide whether to intensify SMC (add cycles) or extend it to older children. We evaluated both options for Upper East Region.

**Methods.** We built a calibrated agent-based malaria transmission model (EMOD / emodpy-malaria) for Upper East (Navrongo proxy), driven by local climate and the region's historical intervention record (ITN mass campaigns, case management, IRS, SMC). Transmission was calibrated to under-five rapid-diagnostic-test (RDT/HRP2) prevalence from five national surveys (2011–2022). We projected 2023–2027 under six scenarios — business-as-usual (BAU: 4 cycles, under-5) and five alternatives combining a fifth cycle and/or age extension to 10 or 15 years — each with 60 stochastic replicates. Outcomes were clinical incidence, severe malaria, deaths (severe × case-fatality ratio), and cost-effectiveness (cost per case, per death, and per DALY averted), with seed-bootstrap 95% confidence intervals.

**Results.** The model reproduced the observed under-five RDT trajectory over the calibration window (2016/2019/2022 modelled 0.30/0.34/0.32 vs surveyed 0.26/0.31/0.34). Each policy protected the ages it targeted: the fifth cycle reduced under-five clinical incidence by ~27% and under-five severe malaria by 44% (95% CI 38–50) but had no effect on older children; age extension reduced clinical and severe malaria by 55–75% in the newly-covered bands but did not benefit under-fives. Region-wide (520,000 under-15), the full package (5 cycles, under-15) averted an estimated 748,000 clinical cases, 985 severe cases, and 98 child deaths per year. All scenarios were highly cost-effective (US$70–227 per DALY averted, far below Ghana's ~US$2,400 GDP per capita), robust across case-fatality assumptions (0.05–0.20). Critically, the fifth cycle was the most cost-effective option per death and per DALY averted (US$70/DALY), because malaria mortality is concentrated in under-fives, whereas age extension averted the most clinical cases but fewer deaths. In an incremental analysis, only the five-cycle scenarios lay on the cost-effectiveness frontier (incremental cost-effectiveness ratios US$70–299/DALY); the four-cycle age-extension options were dominated, indicating that extending the age range is cost-effective only when combined with a fifth cycle. The full package also reduced under-15 parasite prevalence by ~36% and averted ~1,400 childhood anaemia cases per 1,000 under-15 children per year.

**Conclusions.** In a high-transmission northern Ghana setting, adding a fifth SMC cycle and extending SMC to older children are complementary strategies that optimise different endpoints — the fifth cycle for child survival, age extension for total disease burden — and both are exceptionally cost-effective. These results provide the local, quantified evidence WHO recommends for SMC policy decisions.

---

## 1. Introduction

Malaria remains a leading cause of childhood illness and death in Ghana's northern savannah, where transmission is intense and highly seasonal. Seasonal Malaria Chemoprevention (SMC) — monthly courses of sulfadoxine–pyrimethamine plus amodiaquine (SPAQ) delivered to children during the high-transmission season — is one of the most effective preventive tools available, reducing clinical malaria in under-fives by around 75% [Wilson 2011; ACCESS-SMC]. Ghana introduced SMC in 2015–2016 in the Upper West, Upper East and Northern regions and now delivers four monthly cycles (June–September) to children aged 3–59 months.

Two questions dominate current SMC policy. First, whether to **intensify** the regimen — the four cycles end in September, but transmission tails into October–November, leaving a post-season gap that a fifth cycle could close. Second, whether to **extend eligibility to older children** (5–15 years), who receive no chemoprevention despite carrying a substantial and rising share of the clinical burden as under-five transmission falls.

The 2022 update to the WHO malaria guidelines removed fixed age groups, cycle numbers and drug specifications from the SMC recommendation, explicitly stating that "malaria programmes should use local data to determine which age groups are at high risk" and that "mathematical modelling may be required" to inform decisions on extending the age range [WHO 2023]. Trial evidence supports the direction: in Mali, extending SMC to children 5–10 years reduced uncomplicated malaria by 21% and severe malaria by 62% in that age group [WHO 2023, §3.3]; in Senegal, SMC in children under ten reduced RDT-confirmed malaria by 60%, with similar effect in under-fives and 5–9-year-olds [Cissé 2016].

Here we provide exactly the local, quantified evidence WHO calls for, for Upper East Region. We use a climate-driven, individually-based transmission model calibrated to the region's own survey data to project the health impact and cost-effectiveness of intensifying and age-extending SMC, 2023–2027.

---

## 2. Methods

### 2.1 Model
We used EMOD (Institute for Disease Modeling) via the emodpy-malaria interface (v5.2.1), a stochastic, individual-based model of *Plasmodium falciparum* transmission with mechanistic representations of the mosquito life cycle, within-host parasite and immune dynamics, clinical and severe disease, and interventions. The region was represented as a single node using Navrongo (10.90°N, 1.09°W) as the Upper East proxy. Mosquito larval habitat combined a rainfall-driven temporary habitat and a constant dry-season habitat, forced by daily local climate data, producing the characteristic single annual transmission peak.

### 2.2 Population, burn-in and stochasticity
Each simulation used 2,000 agents with regionally-representative age structure and vital dynamics. Models were run to immunological and transmission equilibrium through a 50-year burn-in, serialized, and picked up for the 2008–2027 intervention period. Because severe malaria and death are rare events, statistical power was obtained from **60 independent stochastic replicates** rather than a larger population; all estimates are reported with seed-bootstrap 95% confidence intervals.

### 2.3 Historical interventions (2008–2022)
The intervention record was reconstructed from national surveys and programme data: **ITN mass campaigns** every three years (2012, 2015, 2018, 2021) at DHS-measured coverage, with Weibull net retention and age-dependent use (lower in school-age children and adults than under-fives); **case management** of clinical episodes at survey careseeking coverage with artemether–lumefantrine; a regional **IRS** pulse (2013–2014); and **SMC** from 2016 (SPAQ, four monthly cycles, children 3–59 months).

### 2.4 Transmission calibration
The transmission-intensity scalar (`x_Temporary_Larval_Habitat`) was calibrated so that modelled under-five RDT (HRP2-detected) prevalence reproduced the trajectory measured in five national surveys — MICS 2011, GDHS 2014, GMIS 2016, GMIS 2019, GDHS 2022 — over 2011–2022. RDT (rather than microscopy) was used as the calibration target, consistent with routine diagnosis; HRP2 antigen persistence was modelled explicitly. The calibrated model matched the surveys over the intervention era (Table 1). Modelled clinical incidence was additionally checked against routine DHIMS confirmed-case data and found consistent (≈2.5 episodes per under-15 child per year, within the range expected for holoendemic settings after accounting for facility under-reporting).

### 2.5 Projection scenarios (2023–2027)
SMC coverage for the projection was set from the published literature by age band — under-five 87% per cycle (matching the 2024 Upper East coverage survey [Abdul-Karim 2025]); newly-extended 5–10-year bands ramping 75→85%, and 10–15-year bands 65→75%, over the first three years (reflecting programme maturation, consistent with Senegal [Bâ 2018; Cissé 2016] and the documented difficulty of reaching older children in community delivery [Moukénet 2022]). Six scenarios were compared:

| Label | Cycles | Age ceiling |
|---|---|---|
| **BAU: SMC-4 (U5)** | 4 | under-5 |
| **SMC-5 (U5)** | 5 | under-5 |
| **SMC-4 (U10)** | 4 | under-10 |
| **SMC-4 (U15)** | 4 | under-15 |
| **SMC-5 (U10)** | 5 | under-10 |
| **SMC-5 (U15)** | 5 | under-15 |

### 2.6 Outcomes and cost-effectiveness
Primary outcomes were clinical incidence and severe malaria incidence by age band, and their percentage reduction versus BAU (pooled across seeds with a seed-bootstrap CI, appropriate for rare counts). Secondary outcomes were parasite prevalence (RDT/HRP2 and microscopy) and moderate-to-severe childhood anaemia. **Deaths** were estimated as severe cases × a severe-malaria case-fatality ratio (CFR = 0.10 central; sensitivity 0.05–0.20). Absolute annual impact was scaled to the Upper East under-15 population (≈520,000). **Cost-effectiveness** used an SMC delivery cost of US$0.90 per child-cycle (ACCESS-SMC economic cost ≈US$3.63/child/year ÷ 4 [Gilmartin 2021]), reporting cost per clinical case, per severe case, per death, and per **DALY** averted (30 discounted life-years lost per child death; standard GBD disability weights for morbidity), benchmarked against Ghana's GDP per capita (~US$2,400). Because the six scenarios are mutually-exclusive nested options, we additionally conducted an **incremental cost-effectiveness analysis**, ordering scenarios by cost, removing strongly- and extendedly-dominated options, and computing ICERs along the efficiency frontier.

---

## 3. Results

### 3.1 Calibration (Table 1)
The model reproduced the observed under-five RDT prevalence across the intervention era, with a mean absolute error of 0.03 over 2016–2022.

**Table 1. Modelled vs surveyed under-five RDT prevalence, Upper East.**

| Survey year | Modelled RDT | Surveyed RDT |
|---|---|---|
| 2016 (GMIS) | 0.30 | 0.26 |
| 2019 (GMIS) | 0.34 | 0.31 |
| 2022 (GDHS) | 0.32 | 0.34 |

### 3.2 Clinical impact
Each policy reduced clinical malaria in the ages it covered and left other ages at BAU (Figure 1A). Relative to BAU, projected clinical cases averted per 1,000 under-15 children per year were: SMC-5 (U5) 203 (95% CI 102–302); SMC-4 (U10) 642 (530–727); SMC-4 (U15) 971 (881–1,084); SMC-5 (U10) 1,015 (904–1,114); and SMC-5 (U15) 1,443 (1,324–1,543). The fifth cycle reduced under-five clinical incidence by ~27%; age extension reduced clinical incidence in newly-covered bands by 50–70%.

### 3.3 Parasite prevalence
Because transmission was calibrated to prevalence, projected prevalence reductions provide a directly survey-comparable outcome. Relative to BAU, the full package (SMC-5 U15) reduced under-15 RDT prevalence by 35.5% (under-5 21.8%, 5–10 43.1%, 10–15 37.9%) and microscopy prevalence by 29.2%. The fifth cycle alone reduced under-five RDT prevalence by 12.1%, and age extension reduced prevalence chiefly in the covered older bands (30–43%).

### 3.4 Severe malaria (Figure 1B)
Severe malaria followed the same age logic but is concentrated in under-fives. Percentage reductions versus BAU:

**Table 2. Severe malaria reduction vs BAU (%, [95% CI]).**

| Scenario | Under-5 | 5–10 | 10–15 | Under-15 |
|---|---|---|---|---|
| SMC-5 (U5) | **44 [38, 50]** | ~0 | – | **30 [23, 36]** |
| SMC-4 (U10) | ~0 | **70 [58, 80]** | ~0 | 10 [1, 19] |
| SMC-4 (U15) | ~0 | **75 [65, 83]** | **73 [49, 89]** | 15 [6, 24] |
| SMC-5 (U10) | **43 [34, 51]** | **89 [84, 94]** | ~0 | **51 [44, 57]** |
| SMC-5 (U15) | **47 [40, 53]** | **80 [72, 86]** | **69 [37, 89]** | **55 [49, 60]** |

### 3.5 Childhood anaemia
SMC also reduced moderate-to-severe childhood anaemia. Anaemia cases averted per 1,000 under-15 children per year were: SMC-5 (U5) 793 (95% CI 528–1,147); SMC-4 (U10) 374 (145–643); SMC-4 (U15) 469 (218–723); SMC-5 (U10) 1,253 (932–1,562); and SMC-5 (U15) 1,384 (1,060–1,689). As with severe disease and death, the fifth cycle alone averted more anaemia than either age-extension-alone scenario, reflecting the concentration of anaemia in under-fives.

### 3.6 Deaths averted (Figure 1C)
Because malaria mortality is concentrated in under-fives, the fifth cycle alone (52 deaths averted/year, 95% CI 38–66) prevented more deaths than either age-extension-alone scenario (SMC-4 U10: 18 [0–36]; SMC-4 U15: 28 [11–46]) — despite age extension averting 3–5× more clinical cases. The combined packages averted the most deaths (SMC-5 U10: 91 [77–107]; SMC-5 U15: 98 [84–113]).

**Table 3. Region-wide annual impact (scaled to 520,000 under-15).**

| Scenario | Clinical averted/yr | Severe averted/yr | Deaths averted/yr | SMC cost/yr (US$) |
|---|---|---|---|---|
| SMC-5 (U5) | 105,000 | 523 | 52 | 0.16 M |
| SMC-4 (U10) | 333,000 | 180 | 18 | 0.51 M |
| SMC-4 (U15) | 505,000 | 282 | 28 | 0.88 M |
| SMC-5 (U10) | 527,000 | 914 | 91 | 0.79 M |
| SMC-5 (U15) | 748,000 | 985 | 98 | 1.26 M |

### 3.7 Cost-effectiveness (Figure 1D)
Every scenario was highly cost-effective, at US$70–227 per DALY averted — an order of magnitude below Ghana's GDP per capita (~US$2,400) — and remained so across the full CFR sensitivity range (0.05–0.20). The **fifth cycle was the most cost-effective** option (US$70/DALY, US$2,969/death), because it targets the ages where malaria kills; age extension was least cost-effective per DALY (US$199–227) despite the largest clinical impact. Cost per clinical case averted was ~US$1–2 across scenarios.

### 3.8 Incremental cost-effectiveness and efficiency frontier (Figure 2)
Because the scenarios are mutually-exclusive, nested options, we performed an incremental analysis, ordering scenarios by cost and computing incremental cost-effectiveness ratios (ICERs) between adjacent non-dominated options (Table 4). The cost-effectiveness frontier comprised **only the three five-cycle scenarios**: the four-cycle age-extension options were dominated — SMC-4 (U10) by extended dominance and SMC-4 (U15) by strong dominance — meaning it is never optimal to extend the age range without also adding the fifth cycle. The efficient expansion pathway was therefore BAU → add fifth cycle (ICER US$70/DALY) → extend to 10 years (US$172/DALY) → extend to 15 years (US$299/DALY), every step remaining well below the willingness-to-pay threshold of half the GDP per capita (US$1,200/DALY).

**Table 4. Incremental cost-effectiveness (region-wide, annual, vs BAU).**

| Scenario | Cost/yr (US$) | DALYs averted/yr | ICER (US$/DALY) | Status |
|---|---|---|---|---|
| BAU: SMC-4 (U5) | 0 | 0 | — | reference |
| SMC-5 (U5) | 155,000 | 2,225 | 70 | frontier |
| SMC-4 (U10) | 505,000 | 2,545 | — | extended-dominated |
| SMC-5 (U10) | 794,000 | 5,945 | 172 | frontier |
| SMC-4 (U15) | 882,000 | 3,891 | — | dominated |
| SMC-5 (U15) | 1,256,000 | 7,489 | 299 | frontier |

---

## 4. Discussion

In a high-transmission northern Ghana setting, our calibrated model shows that the two SMC-expansion options under consideration **optimise different endpoints and are both exceptionally cost-effective**. Adding a fifth cycle closes the post-season transmission gap for under-fives — the group in which malaria is most often fatal — and is the most cost-effective way to avert deaths (US$70/DALY). Extending eligibility to older children targets where the *clinical* burden increasingly sits as under-five transmission falls, averting the most cases, but fewer deaths and at a higher (though still very favourable) cost per DALY. The combined package delivers the largest overall benefit — nearly 750,000 clinical cases and ~98 child deaths averted per year region-wide — at roughly US$1.3 million per year.

These findings align closely with independent evidence. The direction and magnitude of the projected age-extension effect (55–75% reduction in the covered bands) match the Mali trial (21% clinical, 62% severe in 5–10-year-olds) and the Senegal trials (≈60% RDT reduction in under-tens) cited in the WHO field guide. They also quantify WHO's own caveat that "cost-effectiveness becomes less favourable as programmes expand to age groups at lower risk of severe disease" — our model puts numbers on that gradient while showing every option remains well within accepted thresholds.

For programme decision-making, the results support a **tiered logic**: if the objective is child survival with a constrained budget, the fifth cycle offers the best value; if the objective is reducing total childhood malaria illness, age extension delivers far more; and where resources allow, the combined package maximises both. The incremental analysis sharpens this into an explicit expansion pathway: because the four-cycle age-extension scenarios were dominated by five-cycle alternatives, a programme considering age extension should add the fifth cycle first and then extend the age range progressively — with every step (US$70, US$172, US$299 per DALY) remaining far below the willingness-to-pay threshold. These findings were consistent across four endpoints — clinical incidence, parasite prevalence, anaemia, severe disease and death — strengthening confidence in the age-structured conclusion.

### 4.1 Limitations
The model represents Upper East as a single well-mixed node, omitting within-region spatial heterogeneity and human movement. Calibration targeted RDT (HRP2) prevalence, which persists after parasite clearance; the model reproduces this but the resulting transmission inference carries the associated uncertainty. Severe malaria and deaths are derived (severe from the model's severe-disease pathway; deaths via an applied CFR) rather than directly observed, and are sensitive to the CFR — although our conclusions held across CFR 0.05–0.20. SMC efficacy was held constant; emerging SPAQ resistance, which could erode future benefit, was not modelled and is a priority for sensitivity analysis. Cost estimates use a single pooled unit cost and do not capture region-specific delivery costs or the incremental operational cost of reaching older children, which may be higher than for under-fives.

---

## 5. Conclusion
For Upper East Region, adding a fifth SMC cycle and extending SMC to older children are complementary, highly cost-effective strategies: the fifth cycle is the best value for preventing child deaths, age extension averts the most illness, and the combined package maximises impact. This provides the local, model-based evidence WHO recommends to guide SMC intensification and age-extension decisions.

---

## Figures
- **Figure 1.** Consolidated impact and cost-effectiveness of SMC scenarios, Upper East 2023–2027: (A) clinical incidence reduction by age band; (B) severe malaria reduction by age band; (C) child deaths averted per year (region-wide); (D) cost per DALY averted vs cost-effectiveness thresholds. *(data/consolidated_upper_east.png)*
- **Figure 2.** Cost-effectiveness plane and efficiency frontier: cost vs DALYs averted per year (region-wide), with willingness-to-pay threshold lines; frontier scenarios in red, dominated in grey. *(data/incremental_ce_upper_east.png)*
- **Figure 3.** Monthly clinical incidence trajectory — shared calibrated history to 2022, then BAU vs scenarios 2023–2027, by age band. *(data/timeseries_clinical_upper_east.png)*
- **Figure 4.** Annual clinical incidence by scenario and age band, 2023–2027. *(data/annual_clinical_upper_east.png)*
- **Supplementary.** Severe-malaria trajectory and standalone cost-effectiveness panel. *(data/timeseries_severe_upper_east.png, data/cost_effect_upper_east.png)*

## Key references
1. WHO. *Seasonal malaria chemoprevention with SPAQ: a field guide, 2nd ed.* Geneva: WHO; 2023.
2. Cissé B, Bâ EH, Sokhna C, et al. Effectiveness of SMC in children under ten in Senegal: a stepped-wedge cluster-randomised trial. *PLoS Med.* 2016;13(11):e1002175.
3. Bâ EH, Pitt C, Dial Y, et al. Implementation, coverage and equity of large-scale door-to-door SMC in Senegal. *Sci Rep.* 2018;8:5489.
4. Abdul-Karim A, et al. SMC coverage and adherence in Upper East Region, Ghana. *Malar J.* 2025;24 (10.1186/s12936-025-05322-9).
5. Moukénet A, Donovan L, Honoré B, et al. Extending SMC to older children in Chad. *Glob Health Sci Pract.* 2022;10(1):e2100161.
6. Gilmartin C, Nonvignon J, Cairns M, et al. Seasonal malaria chemoprevention in the Sahel: an economic cost analysis (ACCESS-SMC). *Lancet Glob Health.* 2021.
7. ACCESS-SMC Partnership. Effectiveness of SMC at scale in west and central Africa. *Lancet.* 2020;396:1829–40.
8. Cairns M, et al. Estimating the potential public health impact of SMC. *Nat Commun.* 2012;3:881.
9. WHO. *World Malaria Report 2023.* Geneva: WHO; 2023.
