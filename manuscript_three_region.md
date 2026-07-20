# Intensifying and age-extending Seasonal Malaria Chemoprevention in the three northern regions of Ghana: an agent-based modelling and cost-effectiveness study

*Draft manuscript — Upper East, Northern and Upper West regions. Author list, affiliations, and journal formatting to be completed.*

---

## Abstract

**Background.** Seasonal Malaria Chemoprevention (SMC) with sulfadoxine–pyrimethamine plus amodiaquine (SPAQ) is delivered to children under five as four monthly cycles in northern Ghana. WHO's 2022/2023 guidance removed fixed age limits and cycle numbers and asks countries to use local data and mathematical modelling to decide whether to intensify SMC (add cycles) or extend it to older children. We evaluated both options across all three high-burden northern regions.

**Methods.** We built calibrated agent-based *P. falciparum* transmission models (EMOD / emodpy-malaria) for Upper East, Northern and Upper West, each driven by local climate and its own historical intervention record (ITN mass campaigns, case management, IRS, SMC). Regional transmission intensity was calibrated to under-five rapid-diagnostic-test (RDT) prevalence from five national surveys (2011–2022), with a dense larval-habitat sweep confirming each best-fit. We projected 2023–2027 under six scenarios — business-as-usual (BAU: 4 cycles, under-5) and five alternatives combining a fifth cycle and/or age extension to 10 or 15 years (denoted SMC-*n* (U*a*) for *n* cycles up to age *a*) — each with 60 stochastic replicates. Outcomes were clinical incidence, parasite prevalence, severe malaria, anaemia, deaths, and cost-effectiveness (cost per case, death and DALY averted; incremental analysis with an efficiency frontier), with seed-bootstrap 95% CIs.

**Results.** All three models reproduced the observed under-five RDT trajectories over the calibration window (mean absolute error 0.04–0.06), with best-fit transmission scalars of 1.8 (Upper East), 2.0 (Northern) and 2.5 (Upper West). In every region the same age logic held: a fifth cycle cut under-five severe malaria by 31–47% but did not benefit older children, while age extension cut clinical and severe malaria by 50–80% in newly-covered bands with little under-five benefit. Deaths, being concentrated in under-fives, were averted more cost-effectively by the fifth cycle than by age extension in all regions. **The incremental analysis produced an identical efficiency frontier in all three regions: only the five-cycle scenarios were non-dominated** — it is never cost-effective to extend the age range without also adding the fifth cycle. Every frontier step was highly cost-effective (incremental cost-effectiveness ratios US$66–299 per DALY, far below Ghana's ~US$2,400 GDP per capita). Scaled to the three regions' ~1.78 million under-15 children, the full package (SMC-5 U15) would avert an estimated **2.5 million clinical cases, ~4,360 severe cases and ~435 child deaths per year** at ~US$4.3 million per year.

**Conclusions.** Across all three northern Ghana regions, adding a fifth SMC cycle and extending SMC to older children are complementary, highly cost-effective strategies that optimise different endpoints — the fifth cycle for child survival, age extension for total disease burden. The consistency of the efficiency frontier across three independently-calibrated regions provides robust, local model-based evidence for SMC intensification and age-extension decisions.

---

## 1. Introduction

Malaria remains a leading cause of childhood illness and death in Ghana's northern savannah, where transmission is intense and sharply seasonal. Seasonal Malaria Chemoprevention (SMC) — monthly courses of SPAQ during the high-transmission season — reduces clinical malaria in under-fives by around 75% and is among the most effective preventive tools available. Ghana introduced SMC in 2015–2016 across the Upper East, Upper West and Northern regions and now delivers four monthly cycles (June–September) to children aged 3–59 months.

Two questions dominate current SMC policy. First, whether to **intensify** the regimen: the four cycles end in September, but transmission tails into October–November, leaving a post-season gap a fifth cycle could close. Second, whether to **extend eligibility to older children** (5–15 years), who receive no chemoprevention despite carrying a growing share of the clinical burden as under-five transmission falls.

WHO's 2022 update removed fixed age groups, cycle numbers and drugs from the SMC recommendation, stating that programmes should "use local data to determine which age groups are at high risk" and that "mathematical modelling may be required" to inform age-range extension. Trial evidence supports the direction — in Mali, extending SMC to 5–10-year-olds reduced uncomplicated malaria by 21% and severe malaria by 62% in that group; in Senegal, SMC in under-tens reduced RDT-confirmed malaria by 60%. Here we provide the local, quantified evidence WHO calls for, for **all three** high-burden northern regions, enabling a robustness check across independently-calibrated settings.

---

## 2. Methods

### 2.1 Model and regions
We used EMOD via emodpy-malaria (v5.2.1), a stochastic individual-based model of *P. falciparum* transmission with mechanistic mosquito, within-host, immune, clinical and severe-disease dynamics. Each region was represented as a single node using a proxy site — Navrongo (Upper East), Tamale (Northern) and Wa (Upper West) — with rainfall-driven larval habitat forced by daily local climate data. Each simulation used 2,000 agents run to equilibrium through a 50-year burn-in; because severe malaria and death are rare, statistical power came from **60 stochastic replicates** rather than a larger population, with all estimates reported with seed-bootstrap 95% CIs.

### 2.2 Historical interventions
Each region's intervention record (2008–2022) was reconstructed from national surveys and programme data: three-yearly **ITN** mass campaigns at DHS coverage with age-dependent net use; **case management** at survey careseeking coverage; region-specific **IRS**; and **SMC** from each region's start year (Upper West 2015, Upper East 2016, Northern 2019). IRS histories differed markedly: a short 2013–14 pulse in Upper East, a sustained district-level programme in Northern, and an AGAMal programme in Upper West.

### 2.3 Transmission calibration
For each region the transmission scalar (`x_Temporary_Larval_Habitat`) was calibrated so modelled under-five RDT (HRP2) prevalence reproduced the trajectory measured in five national surveys (MICS 2011; GDHS 2014, 2022; GMIS 2016, 2019) over 2011–2022. Each best-fit was confirmed with a **dense larval-habitat sweep (x = 0.1–20)**, yielding a clear interior minimum (Table 1, Figure 1). During calibration of Upper West it emerged that assuming region-wide 90% IRS coverage sustained over 2014–2022 over-suppressed modelled transmission (crushing under-five prevalence far below the surveys); representing IRS as a realistic **district-fraction (≈30%) effective coverage** — consistent with the treatment of Northern — resolved this and produced an excellent fit. Regional seasonality was validated against routine DHIMS monthly case data (shape correlation 0.79–0.84).

### 2.4 Projection scenarios (2023–2027)
Projection SMC coverage was set from the published literature by age band (under-five 87% per cycle, matching a 2024 Upper East survey; newly-extended 5–10y bands ramping 75→85% and 10–15y bands 65→75% over the first three years). Six mutually-exclusive scenarios were compared:

| Label | Cycles | Age ceiling |
|---|---|---|
| **BAU: SMC-4 (U5)** | 4 | under-5 |
| **SMC-5 (U5)** | 5 | under-5 |
| **SMC-4 (U10)** | 4 | under-10 |
| **SMC-4 (U15)** | 4 | under-15 |
| **SMC-5 (U10)** | 5 | under-10 |
| **SMC-5 (U15)** | 5 | under-15 |

### 2.5 Outcomes and cost-effectiveness
Primary outcomes were clinical and severe malaria incidence by age band and their percentage reduction versus BAU (pooled across seeds with a seed-bootstrap CI, appropriate for rare counts); secondary outcomes were parasite prevalence and moderate-to-severe anaemia. **Deaths** were estimated as severe cases × a case-fatality ratio (0.10 central; 0.05–0.20 sensitivity), consistent with in-hospital severe-malaria case fatality in African children (8.5–10.9% in the AQUAMAT trial [Dondorp 2010]) and with admission-and-mortality estimates for the region [Camponovo 2017], the wider range reflecting untreated or delayed-presentation cases. Absolute impact was scaled to each region's under-15 population. **Cost-effectiveness** used a delivery cost of US$0.90 per child-cycle (ACCESS-SMC economic cost ≈US$3.63/child/year ÷ 4 cycles [Gilmartin 2021]), reporting cost per case, per death and per **DALY** averted; DALYs combined GBD disability weights for uncomplicated and severe malaria [Salomon 2015] with standard reference life expectancy discounted at 3% (~30 life-years lost per young-child death [GBD 2019]). Cost-effectiveness was benchmarked both against Ghana's GDP per capita (~US$2,400 [World Bank]) and, more conservatively, against opportunity-cost-based health thresholds estimated for Ghana (~US$300–900 per DALY [Ochalek 2018; Woods 2016]); all scenarios fell below even the stricter benchmark. Because the scenarios are mutually-exclusive, an **incremental analysis** ordered them by cost, removed dominated options, and computed ICERs along the efficiency frontier.

---

## 3. Results

### 3.1 Calibration (Table 1, Figure 1)
All three regions calibrated well over the intervention era, with best-fit transmission scalars increasing from Upper East to Upper West.

**Table 1. Regional transmission calibration.**

| Region | Proxy site | Best-fit x | RDT fit 2016–22 (mean\|err\|) | Under-15 population | Note |
|---|---|---|---|---|---|
| Upper East | Navrongo | 1.79 | 0.04 | 520,000 | — |
| Northern | Tamale | 2.0 | 0.06 | 900,000 | — |
| Upper West | Wa | 2.5 | 0.04 | 360,000 | IRS represented as district-fraction |

### 3.2 Age-structured impact (Figures 2–3)
In every region each policy reduced malaria in the ages it covered and left other ages at BAU. The fifth cycle reduced under-five clinical incidence by ~25–30%; age extension reduced clinical incidence in newly-covered bands by 50–70%. Severe malaria followed the same age logic but is concentrated in under-fives (Table 2).

**Table 2. Full package (SMC-5 U15) impact vs BAU, by region.**

| Region | Clinical averted /1000 U15/yr | Severe reduction (U15) | Deaths averted/yr | Cost per DALY (US$) |
|---|---|---|---|---|
| Upper East | 1,443 [1,324–1,543] | 55% | 98 [84–113] | 168 |
| Northern | 1,358 [1,234–1,457] | 49% | 235 [207–265] | 150 |
| Upper West | 1,553 [1,442–1,649] | 60% | 102 [91–114] | 135 |

Parasite prevalence and anaemia moved consistently: the full package reduced under-15 RDT prevalence by ~33–36% and averted ~1,380–2,080 anaemia cases per 1,000 under-15 children per year across regions.

### 3.3 Deaths and the fifth-cycle advantage
Because malaria mortality is concentrated in under-fives, the fifth cycle alone prevented more deaths than either age-extension-alone scenario in every region, despite age extension averting the most clinical cases — the clinical burden lives in older children, but the mortality burden lives in under-fives.

### 3.4 Incremental cost-effectiveness — an identical frontier in all three regions (Table 3, Figure 4)
The incremental analysis produced the **same efficiency frontier in every region: only the three five-cycle scenarios were non-dominated**; the four-cycle age-extension options were dominated (extended or strong dominance). It is therefore never optimal to extend the age range without also adding a fifth cycle. Every frontier step remained far below both Ghana's GDP per capita and the stricter opportunity-cost threshold (~US$300–900/DALY [Ochalek 2018; Woods 2016]).

**Table 3. Efficiency-frontier ICERs (US$/DALY) — the five-cycle expansion pathway, by region.**

| Region | → add 5th cycle | → extend to 10y | → extend to 15y |
|---|---|---|---|
| Upper East | 70 | 172 | 299 |
| Northern | 75 | 142 | 261 |
| Upper West | 66 | 126 | 246 |

### 3.5 Combined regional impact (Table 4)
Scaled to the ~1.78 million under-15 children of the three regions, the full package would avert substantial annual burden at modest cost.

**Table 4. Combined three-region annual impact (full package, SMC-5 U15).**

| Metric | Annual estimate |
|---|---|
| Clinical cases averted | ~2.5 million |
| Severe cases averted | ~4,360 |
| Child deaths averted | ~435 |
| Total SMC cost | ~US$4.3 million |
| Pooled cost per death averted | ~US$9,900 |

Over the five-year horizon this is ~12.7 million clinical cases and ~2,175 child deaths averted for ~US$21.5 million.

### 3.6 Cross-region comparison and inference (Figure 5)
Although the six-scenario *ranking* (the efficiency frontier) is identical across regions, the *magnitude* and *value* of SMC expansion differ in interpretable ways (Table 5, Figure 5).

**Table 5. Cross-region comparison, full package (SMC-5 U15) vs BAU.**

| Region | x | Under-15 pop | Clinical averted /1000/yr | Severe reduction | Deaths averted/yr | Cost per DALY |
|---|---|---|---|---|---|---|
| Upper East | 1.8 | 520,000 | 1,443 | 55% | 98 | US$168 |
| Northern | 2.0 | 900,000 | 1,358 | 49% | 235 | US$150 |
| Upper West | 2.5 | 360,000 | 1,553 | 60% | 102 | US$135 |

Three inferences follow. First, **cost-effectiveness improves monotonically with transmission intensity** (cost per DALY falls from US$168 in Upper East to US$135 in Upper West as calibrated x rises from 1.8 to 2.5): each SMC course averts more where transmission is more intense, so the highest-transmission region is the best value for money. Second, **absolute lives saved scale with population**: Northern averts ~235 child deaths per year — more than half the three-region total — purely because it has the largest child population, even though its *per-child* impact is the lowest. Third, **per-child impact reflects both transmission and the existing intervention background**: Upper West achieves the highest per-child impact (high transmission, lighter effective IRS), while Northern's lower per-child impact reflects its strong sustained IRS suppressing baseline transmission and leaving less headroom for SMC. Thus the two natural prioritisation rules diverge — **for best value-for-money, target the highest-transmission region (Upper West); for the greatest absolute number of lives saved, target the largest-population region (Northern)** — while all three benefit substantially and remain far below the cost-effectiveness threshold.

---

## 4. Discussion

Across three independently-calibrated northern Ghana regions, our models converge on a single, robust conclusion: **the two SMC-expansion options optimise different endpoints and are both exceptionally cost-effective everywhere.** The fifth cycle closes the post-season transmission gap for under-fives — the group in which malaria most often kills — and is the most cost-effective way to avert deaths. Age extension targets where the *clinical* burden increasingly sits as under-five transmission falls, averting the most cases but fewer deaths and at higher (still very favourable) cost per DALY. The combined package delivers the largest overall benefit — ~2.5 million clinical cases and ~435 child deaths averted per year region-wide — at ~US$4.3 million.

The most decision-relevant finding is the **replicated efficiency frontier**: in all three regions the four-cycle age-extension scenarios were dominated by five-cycle alternatives, giving an unambiguous expansion pathway — add the fifth cycle first, then extend the age range progressively, with every step highly cost-effective. That this holds across three settings with different transmission intensities (best-fit x from 1.8 to 2.5), populations and intervention histories strengthens confidence that it is a structural property of the age-distribution of malaria burden, not a region-specific artefact. The findings align with WHO's Mali (21% clinical, 62% severe in 5–10y) and Senegal (60% RDT reduction in under-tens) evidence, and quantify WHO's own caveat that cost-effectiveness declines as programmes expand to lower-risk older ages — while showing every option remains well within accepted thresholds.

### 4.1 Limitations
Each region is represented as a single well-mixed node, omitting within-region spatial heterogeneity and human movement. Calibration targeted RDT (HRP2) prevalence, which persists after parasite clearance; the model reproduces this but the resulting transmission inference carries the associated uncertainty. Severe malaria and deaths are derived (severe from the model's severe-disease pathway; deaths via an applied CFR) and sensitive to the CFR, though conclusions held across 0.05–0.20. A shared larval-habitat *composition* (tuned on Upper East) captures seasonal timing well (correlation ~0.8) but slightly broadens the modelled season relative to routine cases in some regions — partly a routine-reporting artefact. The Upper West IRS coverage was necessarily represented as an effective district-fraction rather than a measured region-wide value. SMC efficacy was held constant; emerging SPAQ resistance was not modelled and is a priority for sensitivity analysis. Cost estimates use a single pooled unit cost and do not capture the potentially higher operational cost of reaching older children.

---

## 5. Conclusion
In all three northern Ghana regions, adding a fifth SMC cycle and extending SMC to older children are complementary, highly cost-effective strategies: the fifth cycle is the best value for preventing child deaths, age extension averts the most illness, and the combined package maximises impact — averting an estimated 435 child deaths and 2.5 million clinical cases per year across the three regions. The consistency of these findings across independently-calibrated settings provides the robust, local, model-based evidence WHO recommends to guide SMC intensification and age-extension decisions.

---

## Figures
- **Figure 1.** Regional RDT calibration (2011–2022): candidate transmission scales (light), best-fit (deep red), observed survey points (black), for each region. *(caltraj_{region}_clean.png)*
- **Figure 2.** Consolidated impact and cost-effectiveness by region: (A) clinical reduction and (B) severe reduction by age band; (C) child deaths averted per year; (D) cost per DALY vs thresholds. *(consolidated_{region}.png)*
- **Figure 3.** Annual clinical incidence 2023–2027 by scenario and age band, colour = age ceiling, linestyle = cycles. *(annual_clinical_{region}.png)*
- **Figure 4.** Cost-effectiveness plane and efficiency frontier by region. *(incremental_ce_{region}.png)*
- **Figure 5.** Cross-region comparison (full package): (A) cost per DALY vs transmission intensity; (B) absolute deaths averted by population; (C) per-child clinical impact. *(region_compare.png)*
- **Supplementary.** Monthly incidence trajectories, severe-malaria panels, seasonality validation. *(timeseries_*, seasonality_{region}.png)*

## Key references
1. WHO. *Seasonal malaria chemoprevention with SPAQ: a field guide, 2nd ed.* Geneva: WHO; 2023.
2. Cissé B, et al. Effectiveness of SMC in children under ten in Senegal. *PLoS Med.* 2016;13(11):e1002175.
3. Bâ EH, et al. Implementation, coverage and equity of large-scale SMC in Senegal. *Sci Rep.* 2018;8:5489.
4. Abdul-Karim A, et al. SMC coverage and adherence in Upper East Region, Ghana. *Malar J.* 2025.
5. Moukénet A, et al. Extending SMC to older children in Chad. *Glob Health Sci Pract.* 2022;10(1):e2100161.
6. Gilmartin C, Nonvignon J, Cairns M, et al. Seasonal malaria chemoprevention in the Sahel subregion of Africa: a cost-effectiveness and cost-savings analysis. *Lancet Glob Health.* 2021;9(2):e199–e210.
7. ACCESS-SMC Partnership. Effectiveness of SMC at scale in west and central Africa. *Lancet.* 2020;396:1829–40.
8. WHO. *World Malaria Report 2023.* Geneva: WHO; 2023.
9. Dondorp AM, Fanello CI, Hendriksen IC, et al. Artesunate versus quinine in the treatment of severe falciparum malaria in African children (AQUAMAT): an open-label, randomised trial. *Lancet.* 2010;376:1647–57.
10. Camponovo F, Bever CA, Galactionova K, Smith T, Penny MA. Incidence and admission rates for severe malaria and their impact on mortality in Africa. *Malar J.* 2017;16:1.
11. Salomon JA, Haagsma JA, Davis A, et al. Disability weights for the Global Burden of Disease 2013 study. *Lancet Glob Health.* 2015;3(11):e712–23.
12. GBD 2019 Diseases and Injuries Collaborators (Vos T, et al.). Global burden of 369 diseases and injuries in 204 countries and territories, 1990–2019. *Lancet.* 2020;396:1204–22.
13. Ochalek J, Lomas J, Claxton K. Estimating health opportunity costs in low-income and middle-income countries: a novel approach and evidence from cross-country data. *BMJ Glob Health.* 2018;3(6):e000964.
14. Woods B, Revill P, Sculpher M, Claxton K. Country-level cost-effectiveness thresholds: initial estimates and the need for further research. *Value Health.* 2016;19(8):929–35.
15. World Bank. GDP per capita (current US$) — Ghana. World Development Indicators.
