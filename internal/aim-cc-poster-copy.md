# AIM-CC 2026 poster copy (updated 2026-07-31)

Paste into Google Slides:
https://docs.google.com/presentation/d/1URtxMiGf5tsyKibmLG0eIXAHNbj9GRmO/edit

**Figures (replace in Slides):** [`docs/assets/aim-cc/`](../docs/assets/aim-cc/)

| File | Use |
|------|-----|
| `01-rank-recovery.png` | Results — known pairs goals→v7.1 |
| `02-track-donut.png` | Results — discovery signals |
| `03-formula-example.png` | Method↔Results bridge |
| `04-dual-track.png` | Method/Discussion — signals ≠ legal forms |
| `05-known-network.png` | Results — packages on known pairs |
| `qr-site-en.png` | Footer QR → site `?lang=en` |

**Live numbers (release):** 1,469 metadata · 77 strategies · 68 Goals · 2,278 edges · tracks 216 / 46 / 2,016 · PIN∩corpus ≈10 · curated known = 4 · method **v7.1**.

---

## Header

**Topic:** IMC Agreement Candidates for Ukrainian Hromadas: Signals from Strategies, Geography, and Networks

**Participant:** Max Semenchuk  
**Affiliation:** W3I Civic Tech Lab / independent research pilot  
**Keywords:** computational social science · NLP · social network analysis · inter-municipal cooperation · institutional texts · field experiment

---

## Introduction *(medium)*

Ukraine’s **decentralization** shifted powers to amalgamated communities (**hromadas**, ~**1,469** mainland). Mandatory development strategies encode local goals; **inter-municipal cooperation (IMC / МСС)** offers five legal forms under Law 1508-VII (delegation, joint project, joint financing, joint enterprise, joint body). Surveys (USAID DOBRE) find the hardest stage is **partner search & communication**, not drafting the contract.

Partner discovery is still mostly relational. Registered agreements exist, but candidates outside someone’s network stay invisible. Strategies are one public signal of intent — not the whole product.

**Research question.** Can we surface **agreement candidates** (who · about what · which legal form) by combining strategy-goal NLP with geography, complementary resources, explicit IMC language, and the existing partnership network — and do such recommendations change contact behaviour?

**Contribution.** An open pilot that (1) ranks pairs with multilingual embeddings + covariates, (2) attaches a rule-based **IMC package** (theme · form), (3) validates against registry-confirmed pairs, and (4) pre-registers a small field test of package recommendations.

---

## Methodology

**Data.** Full metadata universe (1,469). Pilot Goals corpus: **68** / 77 structured strategies. Geo + PIN network from KSE Loc-Data-Hub at analysis time. Ground truth: curated `known` registry pairs (N=4); broader PIN∩corpus ≈10.

**Pipeline.** Retrieve → structure → match → package (`theme`/`form`) → validate. Extra layers (not folded into score): complementary resource↔challenge; explicit IMC intents.

**Scoring (v7.1).** Mean-centered sub-goal embeddings (`multilingual-e5-small`); goals cosine blends bipartite soft-alignment ×0.65 + document-centroid ×0.35 (length/hub mitigation):

\[
\text{score} = 0.60 \cdot \text{goals\_cosine} + 0.25 \cdot \text{geo} + 0.15 \cdot \text{mss\_network}
\]

**Two levels (do not conflate):**

1. **Discovery signals** — how we found the pair: similar strategy · handy neighbour · complementary · explicit ask · network.  
2. **Legal forms** — what we suggest signing (five Law 1508-VII types). Package hypotheses never set `known=true`.

**Figures:** `04-dual-track.png`, `03-formula-example.png`.

---

## Results

| Result | Detail |
|--------|--------|
| Scale | **2,278** ranked edges (CC BY 4.0); signals: **216** thematic · **46** operational · **2,016** mixed |
| Known operational | **Slobozhanske↔Obukhivka** (CNAP): goals-only ~**#1822** → v7.1 ~**#23**; package *ASC — delegation* |
| Known thematic cluster | **Nizhyn–Kozelets–Baturyn** tourism triangle recovers into top ~**#8–#17**; package *tourism — joint project* |
| Product unit | Candidate = pair + `package.label` + 1–3 signal chips (not blended score alone) |
| Validation limit | PIN∩corpus ≈ **10** pairs with Goals on both sides vs ~918 registry edges — coverage, not formula, is the bottleneck |
| New lead (hand-checked) | Halytska↔Dubovetska: shared water project named in strategy text |

**Figures:** `01-rank-recovery.png`, `02-track-donut.png`, `05-known-network.png`.

---

## Discussion

**What works.** Mean-centering + length/hub blend separates boilerplate. Text helps **thematic / multi-purpose** candidates; geo/network recover **operational** service sharing. Separating signals from legal forms matches practitioner needs (DOBRE partner-search bottleneck) without overselling NLP.

**What fails / limits.** Goals under-describe operational IMC. `mss_network` in the score is partly circular for PIN recovery. Template strategies create false literal overlap. Pilot N≪ national strategy coverage.

**Theory.** Aligns with OECD IMC ladders and Hooghe & Marks Type II networks: NLP’s comparative advantage sits higher on the cooperation ladder; lower-ladder services are neighbour problems.

**Next — prospective test (pre-registered draft).** Arms: thematic vs operational vs control recommendations; treatment presents an **agreement package**, not a “strategy twin” score. Primary outcome: reply within 14 days. See `internal/aim-cc-field-experiment-prereg.md`.

**Ask for mentors.** How to validate with sparse registry overlap (N≈10)? Labelling / active learning design for institutional texts? Power and ethics for cold outreach to municipalities?

---

## Conclusion

Corpus methods can rank **IMC agreement hypotheses** and recover known clusters when geography/network enter; a single blended score must not be sold as “strategy match.” Product framing: **candidate agreement (theme · form)** justified by discovery signals.

**Next steps.** Grow Goals into PIN-neighbour hubs; keep overlays separate; field-test package recommendations.

**Data & code.** CC BY 4.0 releases + MIT pipeline · KATOTTG join · complements KSE Loc-Data-Hub.

**QR:** https://maxsemenchuk.github.io/hromada-strategy-collab/?lang=en

---

## Elevator pitch (40 sec)

> Ukrainian hromadas write mandatory strategies and can sign IMC in five legal forms, but partners are still found through networks. We treat strategies, geography, and the existing partnership graph as *discovery signals*, output an *agreement package* (theme · form), and check ranks against the registry. Text finds thematic peers; neighbours find service shares. Next: does a package recommendation raise contact rates?

---

## Selected references

1. Hooghe & Marks (2003), *APSR*.  
2. OECD (2022), *Rebuilding Ukraine…*.  
3. OECD (2026), *How to make inter-municipal co-operation work*.  
4. Provan & Kenis (2008), *JPART*.  
5. Wang et al. (2024), Multilingual E5, arXiv:2402.05672.  
6. KSE Loc-Data-Hub (geography & partnerships).  
7. USAID DOBRE (2024), IMC survey (partner-search bottleneck).
