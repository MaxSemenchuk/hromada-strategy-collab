# AIM-CC 2026 poster copy (updated 2026-08-03)

Paste into Google Slides:
https://docs.google.com/presentation/d/1URtxMiGf5tsyKibmLG0eIXAHNbj9GRmO/edit

**Figures (replace in slides):** [`docs/assets/aim-cc/`](../docs/assets/aim-cc/)

| File | Use |
|------|-----|
| `01-rank-recovery.png` | Results — known pairs goals→v7.1 |
| `02-track-donut.png` | Results — discovery signals |
| `03-formula-example.png` | Method↔Results bridge |
| `04-dual-track.png` | Method/Discussion — signals ≠ legal forms |
| `05-known-network.png` | Results — packages on known pairs |
| `06-pin-corpus-growth.png` | Results/Discussion — validation coverage |
| `qr-site-en.png` | Footer QR → site `?lang=en` |

**Live numbers (2026-08-03 release):**

| Metric | Value |
|--------|-------|
| Metadata universe | **1,469** mainland hromadas |
| Structured strategies | **102** (82 full / 11 partial / 9 proxy) |
| Goals-ready for matching | **93** |
| Ranked edges | **4,278** |
| Discovery tracks | thematic **397** · operational **133** · mixed **3,748** |
| PIN∩corpus (both sides have Goals) | **236** (was ~10 in late July) |
| Curated `known` regression pairs | **4** |
| IMC package browse sidecar | **160** hypotheses + 4 known |
| UA–EU twinning layer | **178** hromadas (separate from Law 1508) |
| Donor-tagged hromadas | **181** |
| Method | **v7.1** |

---

## Header

**Topic:** IMC Agreement Candidates for Ukrainian Hromadas: Signals from Strategies, Geography, and Networks

**Participant:** Max Semenchuk  
**Affiliation:** W3I Civic Tech Lab (open civic-tech pilot) · independent researcher  
**Contact:** max.semenchuk@gmail.com · https://github.com/MaxSemenchuk/hromada-strategy-collab  

**About the author *(1–2 lines, optional footer / badge):***  
Max Semenchuk builds open civic-tech tools with Ukrainian hromadas (W3I Civic Tech Lab). This pilot applies computational social science — NLP, network covariates, and a planned field test — to inter-municipal partner discovery.

**Keywords:** computational social science · NLP · social network analysis · inter-municipal cooperation · institutional texts · field experiment

---

## Introduction *(medium)*

Ukraine’s **decentralization** shifted powers to amalgamated communities (**hromadas**, ~**1,469** mainland). Mandatory development strategies encode local goals; **inter-municipal cooperation (IMC / МСС)** offers five legal forms under Law 1508-VII. DOBRE surveys find the hardest stage is **partner search & communication**, not drafting the contract.

Partner discovery remains mostly **relational** (head-to-head contact, associations, donors). Expert input for this study (Tkachuk / ІГС, 2026-08) stresses that tools do not replace trust — they should reduce uncertainty, surface mutual benefit, and prepare a safer first talk. Under martial law, frozen local elections make current head networks *sticky* but *fragile* after future votes — another reason not to treat personal ties as permanent ground truth.

**Research question.** Can we surface **agreement candidates** (who · about what · which legal form) by combining strategy-goal NLP with geography, complementary resources, explicit IMC language, and the existing partnership network — and do package recommendations raise contact rates?

**Contribution.** An open pilot that (1) ranks pairs with multilingual embeddings + covariates, (2) attaches a rule-based **IMC package** (theme · form), (3) validates against the registry as Goals coverage grows, and (4) pre-registers a small field test of recommendations.

---

## Methodology

**Data.** Full metadata (1,469). Goals corpus: **93** / **102** structured strategies (grew via western PIN-hub retrieval). Geo + PIN from KSE Loc-Data-Hub at analysis time. Curated `known` pairs (N=4) for hard regression; PIN∩corpus now **236** pairs with Goals on both sides. Local JSON release (CC BY 4.0); no live NocoDB dependency.

**Pipeline.** Retrieve → structure → match → package (`theme`/`form` via `mss_suggest` / `mss_candidate`) → validate. Extra layers not folded into score: complementary resource↔challenge; explicit IMC intents; UA–EU twinning (separate legal layer).

**Scoring (v7.1).** Mean-centered sub-goal embeddings (`multilingual-e5-small`); goals cosine = bipartite soft-align ×0.65 + document-centroid ×0.35 (length/hub mitigation):

\[
\text{score} = 0.60 \cdot \text{goals\_cosine} + 0.25 \cdot \text{geo} + 0.15 \cdot \text{mss\_network}
\]

**Two levels (do not conflate):**

1. **Discovery signals** — similar strategy · handy neighbour · complementary · explicit ask · network.  
2. **Legal forms** — five Law 1508-VII types. Package hypotheses never set `known=true`.

**Figures:** `04-dual-track.png`, `03-formula-example.png`.

---

## Results

| Result | Detail |
|--------|--------|
| Scale | **4,278** ranked edges; signals: **397** thematic · **133** operational · **3,748** mixed |
| Known operational | **Slobozhanske↔Obukhivka** (CNAP): goals-only **#3383** → v7.1 **#156**; package *ASC — delegation* |
| Known thematic cluster | **Nizhyn–Kozelets–Baturyn**: recover to ~**#115–#127**; curated package *tourism — joint project* |
| Product unit | Candidate = pair + package label + 1–3 signal chips (`mss-candidates.json`) |
| Validation growth | PIN∩corpus **~10 → 236** after corpus growth into PIN hubs (see `06-pin-corpus-growth.png`) |
| Practitioner lead | Water / shared basins flagged as near-term thematic window (Tkachuk) |
| Hand-checked lead | Halytska↔Dubovetska: shared water project named in strategy text |

**Figures:** `01-rank-recovery.png`, `02-track-donut.png`, `05-known-network.png`, `06-pin-corpus-growth.png`.

**Note on ranks.** Absolute known ranks moved as the edge set grew (~2.3k → ~4.3k); the *relative* finding holds: geo/network recover operational pairs that pure goals miss.

---

## Discussion

**What works.** Mean-centering + length/hub blend separates boilerplate. Text helps **thematic** candidates; geo/network recover **operational** service sharing. Separating signals from legal forms matches the DOBRE partner-search bottleneck without overselling NLP. Growing Goals into PIN neighbours made registry validation denser (236 vs ~10).

**What fails / limits.** Goals still under-describe many operational deals. `mss_network` in the score is partly circular for PIN recovery. Template strategies create false literal overlap. Auto `suggested_theme` can misfire on known tourism edges — curated labels still needed for stakeholder copy. Coverage remains a pilot vs ~870 nationally approved strategies.

**Theory / context.** OECD IMC ladders + Hooghe & Marks Type II networks; sticky/fragile heads under frozen elections.

**Next — prospective test (draft prereg).** Arms: thematic vs operational vs control; treatment = **agreement package** recommendation. Primary: reply ≤14 days. `internal/aim-cc-field-experiment-prereg.md` (sampling frame should be refreshed to ~93 Goals / current track counts before freeze).

**Ask for mentors.** With PIN∩corpus now hundreds, how to move from recovery diagnostics to confirmatory validation / labelling? Design and ethics for cold outreach to municipalities? Active learning on institutional texts?

---

## Conclusion

Corpus methods can rank **IMC agreement hypotheses** and recover known clusters when geography/network enter; a single blended score must not be sold as “strategy match.” Product framing: **candidate agreement (theme · form)** justified by discovery signals. Corpus growth into the registry graph is as important as scoring tweaks.

**Next steps.** Keep growing PIN-neighbour Goals; field-test package recommendations; keep overlays separate in stakeholder tools.

**Data & code.** CC BY 4.0 releases + MIT pipeline · KATOTTG join · complements KSE Loc-Data-Hub · site: https://maxsemenchuk.github.io/hromada-strategy-collab/?lang=en

---

## Elevator pitch (40 sec)

> Ukrainian hromadas write strategies and can sign IMC in five legal forms, but partners are still found through networks. We treat strategies, geography, and the partnership graph as *discovery signals*, output an *agreement package* (theme · form), and check ranks as Goals coverage of the registry grows (PIN∩corpus ~10 → 236). Text finds thematic peers; neighbours find service shares. Next: does a package recommendation raise contact rates?

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

## Changelog vs 2026-07-31 poster draft

- Corpus: 68→**93** Goals; 77→**102** structured; edges 2,278→**4,278**  
- PIN∩corpus: ~10→**236** (new fig `06`)  
- Tracks: 216/46 → **397/133**  
- Product/method: МСС-first package framing; v7.1 length/hub; Tkachuk + sticky/fragile heads  
- Known ranks refreshed on larger edge set (CNAP #3383→#156)  
- Optional author blurb added
