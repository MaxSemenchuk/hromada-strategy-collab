# AIM-CC 2026 poster copy (updated 2026-08-04)

Paste into Google Slides:
https://docs.google.com/presentation/d/1URtxMiGf5tsyKibmLG0eIXAHNbj9GRmO/edit

**Figures (replace in slides):** [`docs/assets/aim-cc/`](../docs/assets/aim-cc/)

| File | Use |
|------|-----|
| `01-rank-recovery.png` | Results — dumbbell: goals-only → v7.1 (core N=4) |
| `02-track-donut.png` | Results — discovery signals |
| `03-formula-example.png` | Method↔Results bridge |
| `04-dual-track.png` | Method/Discussion — signals ≠ legal forms |
| `05-known-network.png` | Results — packages on known pairs |
| `06-pin-corpus-growth.png` | Results/Discussion — validation coverage |
| `qr-site-en.png` | Footer QR → site `?lang=en` |

**Live numbers (2026-08-03 release, wave C):**

| Metric | Value |
|--------|-------|
| Metadata universe | **1,469** mainland municipalities (*hromadas*) |
| Structured strategies | **109** (88 full / 12 partial / 9 proxy) |
| Goals-ready for matching | **100** |
| Ranked edges | **4,950** (= C(100,2)) |
| Discovery tracks | thematic **455** · operational **150** · mixed **4,345** |
| PIN∩corpus (both sides have Goals) | **246** (was ~10 in late July) |
| Curated `known` regression pairs | **12** (4 core + 8 registry-approved 2026-08-04) |
| IMC package browse sidecar | **160** hypotheses + 4 known |
| UA–EU twinning layer | **178** hromadas (separate from Law 1508) |
| Donor-tagged hromadas | **181** |
| Method | **v7.1** |

---

## Header

**Topic:** IMC Agreement Candidates for Ukrainian Municipalities: Signals from Strategies, Geography, and Networks

**Participant:** Max Semenchuk  
**Affiliation:** W3I Civic Tech Lab (open civic-tech pilot) · independent researcher  
**Contact:** max.semenchuk@gmail.com · https://github.com/MaxSemenchuk/hromada-strategy-collab  

**About the author *(1–2 lines, optional footer / badge):***  
Max Semenchuk builds open civic-tech tools with Ukrainian municipalities (W3I Civic Tech Lab). This pilot applies computational social science — NLP, network covariates, and a planned field test — to inter-municipal partner discovery.

**Keywords:** computational social science · NLP · social network analysis · inter-municipal cooperation · institutional texts · field experiment

---

## Introduction *(medium)*

Ukraine’s **decentralization** shifted powers to amalgamated municipalities (**hromadas**, ~**1,469** mainland). Mandatory development strategies encode local goals; **inter-municipal cooperation (IMC / МСС)** offers five legal forms under Law 1508-VII. DOBRE surveys find the hardest stage is **partner search & communication**, not drafting the contract.

Partner discovery remains mostly **relational** (head-to-head contact, associations, donors). Expert input for this study (Tkachuk / ІГС, 2026-08) stresses that tools do not replace trust — they should reduce uncertainty, surface mutual benefit, and prepare a safer first talk. Under martial law, frozen local elections make current head networks *sticky* but *fragile* after future votes — another reason not to treat personal ties as permanent ground truth.

**Research question.** Can we surface **agreement candidates** (who · about what · which legal form) by combining strategy-goal NLP with geography, complementary resources, explicit IMC language, and the existing partnership network — and do package recommendations raise contact rates?

**Contribution.** An open pilot that (1) ranks pairs with multilingual embeddings + covariates, (2) attaches a rule-based **IMC package** (theme · form), (3) validates against the registry as Goals coverage grows, and (4) pre-registers a small field test of recommendations.

---

## Methodology

**Data.** Metadata for **1,469** mainland municipalities (*hromadas*). Goals corpus: **100** / **109** structured strategies (grown via high-degree hubs in the registered IMC network, esp. western Ukraine). From **KSE Loc-Data-Hub** at analysis time: geography + registered IMC partnership network. MinRegion registry titles/forms enrich known edges. Open release (CC BY 4.0).

**Pipeline.** Retrieve → structure Goals → match → attach IMC **package** (theme · legal form) → validate. Extra layers **not** folded into the combined score: complementary resources/DREAM ↔ Challenges; explicit IMC language in strategies; UA–EU twinning (separate legal layer).

**Scoring (v7.1) — ranking only, not the outreach message.** Mean-centered sub-goal embeddings (`multilingual-e5-small`); goals cosine = bipartite soft-align ×0.65 + document-centroid ×0.35 (length/hub mitigation):

\[
\text{score} = 0.60 \cdot \text{goals\_cosine} + 0.25 \cdot \text{geo} + 0.15 \cdot \text{mss\_network}
\]

**Product unit (do not conflate with score):**

1. **Discovery signals** — how we found the pair: similar strategy · handy neighbour · complementary · explicit ask · existing network.  
2. **IMC package hypothesis** (theme · one of five legal forms) — what we suggest discussing; not a verified agreement.

**Validation.**

| Layer | N | Role |
|-------|---|------|
| Curated `known` (registry theme·form checked) | **12** | Hard rank recovery regression |
| IMC∩Goals (both sides have Goals + registered link) | **246** | Coverage / soft diagnostics (partly circular via `mss_network`) |

**Figures:** `04-dual-track.png`, `03-formula-example.png`.

---

## Results

On **100** Goals-ready municipalities we rank **4,950** pairs (tracks: **455** thematic · **150** operational · **4,345** mixed). The product unit is an **IMC package hypothesis** (theme · form) plus 1–3 discovery-signal chips — not the blended score alone.

**Known-pair recovery (curated N=12).** Operational ASC **Slobozhanske↔Obukhivka**: goals-only **#3886** → v7.1 **#162** (package *ASC — delegation*). Tourism triangle **Nizhyn–Kozelets–Baturyn** recovers to ~**#124–#133** (curated *tourism — joint project*). Several newer registry-checked pairs land in the top ranks (e.g. Verkhovyna–Kuty **#1**, Halych–Dubivtsi **#2** on the Dniester Canyon tourism agreement #721). Absolute ranks shift as the edge set grows; the relative finding holds: geo/network recover operational deals that pure goals miss.

**Validation coverage.** Growing Goals into IMC-network hubs lifted IMC∩Goals from ~**10** to **246** pairs with strategy text on both sides; curated hard labels grew **4 → 12**.

**Practice note.** Tkachuk flags water/shared basins as a near-term cooperation window. Halych–Dubivtsi illustrates signal vs registry: strategy text mentions water, while the linked registry edge is the multi-party *tourism* canyon project — package must follow the verified agreement subject.

**Figures:** `01-rank-recovery.png` (dumbbell), `02-track-donut.png`, `05-known-network.png`, `06-pin-corpus-growth.png`.

---

## Discussion

**What works.** Mean-centering + length/hub blend separates boilerplate. Text helps **thematic** candidates; geo/network recover **operational** service sharing. Separating signals from legal forms matches the DOBRE partner-search bottleneck without overselling NLP. Growing Goals into IMC-network neighbours densified registry overlap (246 vs ~10); curated known now **N=12**.

**What fails / limits.** Goals still under-describe many operational deals. `mss_network` in the score is partly circular for IMC-network recovery. Template strategies create false literal overlap. Auto `suggested_theme` can misfire — curated labels still needed for stakeholder copy. Coverage remains a pilot vs ~870 nationally approved strategies.

**Theory / context.** OECD IMC ladders + Hooghe & Marks Type II networks; sticky/fragile heads under frozen elections.

**Next — prospective experiment (draft prereg).** Arms: thematic vs operational vs control; treatment = **agreement package** recommendation. Primary: reply ≤21 days. Sampling frame (2026-08): **~100** Goals · **455** thematic · **150** operational — see `internal/aim-cc-field-experiment-prereg.md`.

**Ask for mentors.** With IMC∩Goals in the hundreds and curated known at 12, how to move from recovery diagnostics to confirmatory validation / labelling? Design and ethics for cold outreach to municipalities? Active learning on institutional texts?

---

## Conclusion

Partner search remains the hard step of Ukrainian IMC; strategies, geography, and the registered partnership network are usable **discovery signals**, not a substitute for trust between heads. Combining goal NLP with geo/network **recovers** registry-confirmed pairs that text alone misses — especially **operational** service sharing (e.g. shared ASC) — while text remains stronger for **thematic** clusters. The right product unit is an **agreement-package hypothesis** (who · about what · which legal form) backed by 1–3 signal chips, not a single blended “compatibility” score.

Growing Goals into IMC-network hubs mattered as much as formula tweaks: IMC∩Goals rose ~10→246; curated known labels now N=12. The pilot also ships an **open release** (CC BY 4.0) and a stakeholder map/interface so candidates can be inspected, not only ranked. Limits remain real: sparse national strategy coverage, template-text collisions, and partial circularity when network enters the score.

**Next.** Pre-register and run a small field experiment: do package recommendations raise contact rates vs geo-only / control? Longer term: motivation-conditioned (agent-centric) recommendations per municipality, and clearer validation of package plausibility — not only rank recovery.

**Data & code.** MIT pipeline · KATOTTG join with KSE Loc-Data-Hub · https://maxsemenchuk.github.io/hromada-strategy-collab/?lang=en

---

## Elevator pitch (40 sec)

> Ukrainian municipalities (*hromadas*) write strategies and can sign IMC in five legal forms, but partners are still found through networks. We treat strategies, geography, and the partnership graph as *discovery signals*, output an *agreement package* (theme · form), and check ranks as Goals coverage of the registry grows (PIN∩corpus ~10 → 246). Text finds thematic peers; neighbours find service shares. Next: does a package recommendation raise contact rates?

---

## Selected references

1. Hooghe & Marks (2003), *APSR*.  
2. OECD (2022), *Rebuilding Ukraine…*.  
3. OECD (2026), *How to make inter-municipal co-operation work*.  
4. Provan & Kenis (2008), *JPART*.  
5. Wang et al. (2024), Multilingual E5, arXiv:2402.05672.  
6. KSE Loc-Data-Hub (geography & partnerships).  
7. USAID DOBRE (2024), IMC survey (partner-search bottleneck).

---

## Changelog vs 2026-08-03 poster draft

- Wave C rematch: Goals **93→100**; structured **102→109**; edges **4,278→4,950**; PIN∩corpus **236→246**  
- Tracks: 397/133 → **455/150**  
- Known ranks refreshed (CNAP #3886→#162; triangle ~#124–#133)  
- Title: *Hromadas* → **Municipalities** (EN audience); *hromada* kept on first mention  
- Prereg sampling frame pointer aligned to Aug release
