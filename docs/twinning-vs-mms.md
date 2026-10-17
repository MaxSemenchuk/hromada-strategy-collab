# Two Networks of Cooperation: Which Ukrainian Hromadas Have EU Twin Cities and Which Have Inter-Municipal Cooperation Agreements

**Max Semenchuk** (W3I) · max.semenchuk@gmail.com
Preprint, version 1 · 17 October 2026 · [Ukrainian version](twinning-vs-mms.uk.md)
Data and code: [Hromada Strategy Collaboration Mapping](https://github.com/MaxSemenchuk/hromada-strategy-collab), DOI [10.5281/zenodo.22552879](https://doi.org/10.5281/zenodo.22552879) (CC BY 4.0)

## Abstract

Ukrainian territorial communities (hromadas) cooperate through at least two
channels that policy discussions often treat as one: twinning with municipalities
in the European Union, and inter-municipal cooperation (IMC) agreements with
domestic neighbours under Law 1508-VII. Joining open registry data for all 1,463
hromadas on the KATOTTG administrative code, we find that 326 hromadas have a
registry-confirmed EU partner, 415 were party to an IMC agreement active on
24 February 2022, and only 111 are in both groups (φ = 0.07). Twinning rises
steeply with population (2.6% of hromadas under 5,000 inhabitants; 70.5% of
those above 50,000), whereas IMC participation does not (31.7% and 25.3%). In
logistic models with oblast fixed effects, population has opposite effects on
the two outcomes (odds ratio per tenfold increase: 46.8 for twinning, 0.46 for
IMC), while own income per capita and participation in donor programmes raise
the odds of both. Controlling for these factors, twinning is at most a weak
predictor of IMC (OR 1.36, 95% CI 0.95–1.95). Support instruments designed for
one network therefore cannot be assumed to reach communities active in the
other. Limitations include a pre-war IMC snapshot, incomplete twinning
registries and keyword-based theme classification.

**Keywords:** inter-municipal cooperation; municipal twinning; Ukraine; decentralisation; hromada; open data

## 1. Introduction

Since the amalgamation reform that began in 2015, Ukraine's local self-government has been
organised around roughly 1,450 territorial communities (hromadas). Two forms of
cooperation between hromadas and other municipalities are especially visible in
donor programming. The first is *inter-municipal cooperation* (IMC) between
Ukrainian communities, regulated by the Law "On Cooperation of Territorial
Communities" (1508-VII), which provides five legal forms — among them delegation
of tasks, joint municipal enterprises, joint projects and joint financing of
institutions — and a state registry of agreements. The second is *twinning* and
solidarity partnerships with municipalities abroad, which surged after February
2022, supported by networks such as the German Service Agency Communities in One
World (SKEW) and by donor matchmaking.

Policy documents frequently refer to both under the umbrella of "municipal
cooperation" [1, 2]. Yet the two differ in partners, resources and purpose: a
shared administrative-services centre between two villages and a partnership
with a German city that delivers generators and training are different
activities, probably available to different kinds of communities. A survey of 546
hromadas by USAID DOBRE found that the hardest stage of domestic IMC is partner
search and communication (30% of respondents) rather than legal form [3],
suggesting that how communities find partners may shape who participates.

This paper asks two descriptive questions. (1) Which hromadas take part in each
network? (2) Do the networks overlap beyond what shared community characteristics
would predict? We answer them by joining registry data on both networks with
community-level covariates through a common administrative key.

## 2. Data and methods

### 2.1 Unit of analysis and key

The universe is the 1,463 hromadas of the open dataset *Hromada Strategy
Collaboration Mapping* (government-controlled territory plus hromadas listed as
occupied). All joins use the KATOTTG code, which is unique across the universe;
hromada names are not unique and were not used as keys.

### 2.2 Twinning

A hromada is classified as *twinned* if it has at least one partner with
confidence level "registry" in the dataset's twinning layer. Registry sources
are the SKEW list of German–Ukrainian municipal partnerships (110 hromadas), the
AFCCRE directory of French *jumelages* (44) and the partnership map of the
Ukrainian ministry on decentralization.ua (282); hromadas may appear in several
sources. Weaker evidence (news items, mentions in hromada strategies) accounts
for 27 of 1,371 partner links and is excluded.

### 2.3 Inter-municipal cooperation

A hromada is classified as *IMC-active* if it is a party to an agreement in the
Ukrainian registry of cooperation agreements (data.gov.ua, file dated
28 December 2022) that was in force on 24 February 2022. This yields 306
agreements and 415 hromadas. The mapping from agreements to hromadas is taken
from the KSE-Loc-Data-Hub network table [4]. The flag is therefore a pre-invasion
snapshot, whereas twinning data include partnerships formed later.

### 2.4 Covariates

Population (2022) and own budget income per capita come from KSE data [4].
Digital-participation level is derived from the e-dem.ua platform statistics
(tiers: high, medium, low, not connected). Participation in donor or technical
assistance programmes (DOBRE, DECIDE, GIZ, U-LEAD, EGAP, DESPRO, UNDP, among
others) is recorded in the dataset's `DonorsPrograms` field and is a lower bound
on actual participation.

### 2.5 Analysis

We report shares with 95% Wilson intervals across population bands, settlement
type, oblast, income quartile, e-dem tier and donor participation, and the φ
coefficient for overlap, overall and within population bands. We then fit
logistic regressions for (a) twinning, (b) IMC and (c) IMC with twinning as an
additional predictor. Predictors are log₁₀ population, log₁₀ own income per
capita, e-dem tier (reference: not connected), any donor programme and oblast
fixed effects; 1,415 hromadas with known population and income enter the models.
Odds ratios for population and income refer to a tenfold increase.

For topics, we classified the titles and forms of 899 registry IMC agreements and
the 196 foreign agreements in the Law 3668-IX register [5] with one keyword
vocabulary, allowing multiple topics per agreement. Because the 3668-IX register
records formal international agreements rather than twinning as such, this
comparison is indicative only.

All numbers are produced by a single script (Section 7).

## 3. Results

### 3.1 Who takes part

Overall, 326 hromadas (22.3%) are twinned and 415 (28.4%) are IMC-active.
Table 1 shows participation by population band.

**Table 1.** Share of hromadas with twinning and IMC by population (95% Wilson CI).

| Population | Hromadas | Twinned | IMC-active |
|---|---|---|---|
| < 5,000 | 265 | 2.6% (1.3–5.4) | 31.7% (26.4–37.5) |
| 5,000–10,000 | 417 | 9.8% (7.3–13.1) | 29.0% (24.9–33.5) |
| 10,000–20,000 | 383 | 20.1% (16.4–24.4) | 27.7% (23.4–32.4) |
| 20,000–50,000 | 299 | 44.8% (39.3–50.5) | 26.8% (22.1–32.0) |
| > 50,000 | 95 | 70.5% (60.7–78.8) | 25.3% (17.6–34.8) |

(Four hromadas with unknown population are omitted.) Twinning rises
monotonically with size; IMC participation is nearly flat and slightly higher in
the smallest communities. By settlement type, 51% of urban, 15% of settlement
and 9% of rural hromadas are twinned, versus 28%, 22% and 33% for IMC.

Geography also differs. Twinning is concentrated in the west — Lviv (62%),
Zakarpattia (58%) and Volyn (50%) oblasts — while IMC participation is highest in
Rivne (59%), where only 6% of hromadas are twinned, followed by Lviv (58%),
Poltava (57%) and Ivano-Frankivsk (47%). Kyiv oblast has 32% twinned and 14%
IMC-active hromadas.

### 3.2 Overlap

Of 415 IMC-active hromadas, 111 (26.7%) are also twinned; 215 are twinned only,
304 IMC-active only, and 833 in neither group. The φ coefficient is 0.07. Overlap
is not merely a size effect: within population bands φ ranges from 0.04 to 0.13,
a small positive association.

### 3.3 Correlates of participation

**Table 2.** Odds ratios (95% CI) from logistic regressions with oblast fixed
effects (n = 1,415).

| Predictor | Twinning | IMC |
|---|---|---|
| Population, ×10 | 46.8 (24.5–89.4) | 0.46 (0.31–0.66) |
| Own income per capita, ×10 | 2.80 (1.51–5.19) | 2.02 (1.29–3.17) |
| Any donor programme | 1.75 (1.09–2.81) | 1.90 (1.30–2.78) |
| e-dem "high" vs not connected | 1.77 (1.05–2.98) | 1.39 (0.88–2.21) |

Population acts in opposite directions: conditional on the other covariates and
oblast, larger hromadas are far more likely to be twinned and somewhat less likely
to be IMC-active. Income and donor participation raise the odds in both networks
by similar amounts (confidence intervals overlap). High digital participation is
associated with twinning (p = 0.03) but not significantly with IMC. When twinning
is added to the IMC model, its odds ratio is 1.36 (0.95–1.95; p = 0.09).

Donor-programme patterns differ by programme, though subsamples are small. Of 20
hromadas tagged with GIZ, 16 (80%) have a German partner in SKEW, compared with
7.5% of all hromadas; GIZ is consistent with its role as operator of the German
partnership scheme. DOBRE hromadas are more often IMC-active (40%) than twinned
(24%), as are U-LEAD hromadas (81% and 56%).

### 3.4 Topics

**Table 3.** Most frequent topics (share of agreements; multi-label).

| Domestic IMC registry (n = 899; 37% unclassified) | | Foreign agreements, Law 3668-IX (n = 196; 14% unclassified) | |
|---|---|---|---|
| Roads and infrastructure | 21% | Culture | 72% |
| Education | 14% | Education | 55% |
| Administrative-services centres | 11% | Economy | 53% |
| Health | 9% | Tourism | 47% |
| Social services | 6% | Governance | 32% |
| Waste | 5% | Roads | 26% |
| Fire protection | 4% | Cross-border cooperation | 22% |

Domestic agreements are dominated by service delivery; foreign agreements by
broad cultural, educational and economic exchange. The latter frequently use
generic wording ("trade-economic, scientific-technical and cultural
cooperation"), which assigns several topics to one agreement and inflates their
shares. Energy appears in under 1% of both registers, although it is frequently
cited as a priority of partnership programmes; plausibly, it is realised through
projects and humanitarian assistance rather than signed agreements.

## 4. Discussion

The two networks recruit different communities. Twinning behaves like a resource
that scales with the size and administrative capacity of a municipality; IMC
is consistent with a response to local needs that is, if anything, at least as common where
communities are small and may be unable to provide services alone. That donor participation
and income matter for both networks suggests that some general capacity to
cooperate exists, but its effect on the odds is similar and modest, and being in
one network adds little to the odds of being in the other once these factors are
controlled.

Three implications follow, each as a hypothesis rather than a finding. First,
programmes that fund international partnerships and programmes that fund
inter-municipal cooperation reach largely different communities; coordination
should not assume that the former builds capacity for the latter. Second, small
rural hromadas are well represented in IMC but rarely appear in twinning
registries, so any new instrument for connecting them with EU peers faces a
distinct starting point. Third, the strong western concentration of twinning, and
the Rivne–Poltava concentration of IMC, indicate regional ecosystems — donors,
facilitators and associations — worth studying directly.

DOBRE's finding that partner search is the main obstacle to IMC [3] fits with
these observations: twinning has dedicated matchmaking mechanisms (SKEW and
similar schemes), whereas domestic IMC has no comparable national scheme. We
did not test whether differences in partner search explain these patterns.

## 5. Limitations

1. **Timing.** The IMC flag is a pre-invasion snapshot; twinning includes
   partnerships formed after 2022. This may amplify the difference by
   size. A current public IMC registry would be needed to check.
2. **Incomplete twinning registries.** SKEW covers Germany, AFCCRE France; other
   countries come from the ministry's map. True twinning is more extensive and
   coverage varies by country.
3. **Association, not causation.** The models adjust for observed
   characteristics only. Interpretations such as international-relations capacity
   in large municipalities are conjectures.
4. **Topics.** Classification uses keywords on free text; a large share of IMC
   agreements (generic joint projects and enterprises) remains unclassified, and the
   3668-IX register differs from twinning.
5. **Measurement.** Donor participation is a lower bound; population for
   some occupied hromadas is a 2022 estimate and unknown for four.
6. **Single snapshot.** No temporal dynamics are examined.

## 6. Conclusion

In Ukraine, EU twinning and domestic inter-municipal cooperation are largely
separate networks recruiting different kinds of communities. Size is the main
dividing line, with opposite effects; income and donor engagement favour both.
Treating them as one phenomenon in policy design, evaluation or support
programmes risks missing most of the communities in the other network.

## 7. Data and code availability

All inputs except two re-fetchable caches are released in
[`data/releases/`](https://github.com/MaxSemenchuk/hromada-strategy-collab/tree/main/data/releases)
(CC BY 4.0; dataset card: `DATASET.md`; CSV mirrors in `csv/`). The IMC registry
(`yarn fetch-mss-registry`) and the KSE network table [4] are cached under
`data/cache/` and are not redistributed. The script
[`scripts/analysis/twinning_vs_mms.py`](../scripts/analysis/twinning_vs_mms.py)
reproduces every number in this paper and writes
`internal/twinning-vs-mms-results.json`; the regression block requires `pandas`
and `statsmodels`.

## References

1. OECD. *How to Make Inter-Municipal Co-operation Work.* OECD, 2026.
2. OECD. *Rebuilding Ukraine by Reinforcing Regional and Municipal Governance.* OECD Publishing, 2022.
3. USAID DOBRE. *Inter-municipal cooperation of territorial communities: research results* (survey of 546 hromadas and analysis of post-2020 agreements). Presentation, 2024, decentralization.ua.
4. KSE Institute. *KSE-Loc-Data-Hub* (v1.0.1). Zenodo, 2025. https://doi.org/10.5281/zenodo.15267573
5. Law of Ukraine 3668-IX and Resolution of the Cabinet of Ministers 357-2025: register of agreements on international territorial cooperation, data.gov.ua.
6. Law of Ukraine "On Cooperation of Territorial Communities", No. 1508-VII (2014).
7. Engagement Global / SKEW. List of German–Ukrainian municipal partnerships. https://skew.engagement-global.de
8. AFCCRE. *Annuaire des communes jumelées* (snapshot 2 September 2025).

**Suggested citation.** Semenchuk, M. (2026). Two networks of cooperation: which
Ukrainian hromadas have EU twin cities and which have inter-municipal
cooperation agreements. Preprint v1. Hromada Strategy Collaboration Mapping.
https://doi.org/10.5281/zenodo.22552879
