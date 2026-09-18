# UA–EU municipal twinning — format insights

Research notes (2026-07-29 layer build; narrative insights 2026-08-03).
**Separate from domestic МСС** (Law 1508-VII). Data: `yarn twinning` →
[`twinning-partners.json`](../data/releases/twinning-partners.json).
Sources: [external-data-sources.md](./external-data-sources.md#skew--germanukrainian-municipal-partnerships-twinning).

Do **not** treat twinning as Law 1508-VII МСС, and never set `known: true` from
it. Registry-confidence twinning (SKEW / decentralization.gov.ua) is a **weak
pairwise input** to `social_capital` (the 0.15 readiness slot: both sides
practiced an international partnership). Product overlay label stays
`місто-побратим ЄС` — node highlight, not a domestic IMC edge.

---

## What the format is (post-2022)

Not symbolic sister-city branding alone. Typical cycle:

1. **Need-driven start** — equipment, generators, water, health, IDP support
2. **Online intro** (often with interpreters) → memo / informal solidarity
3. **Delegation visits** (SKEW can fund kick-off visits: ~5 people / ~5 days)
4. **Thematic tracks** — civil defence / crisis, energy, water–waste, education,
   social services, local economy / B2B
5. Sometimes a **formal twin-city agreement** after a year+ of real work

It is **city↔city**, not an «EU grant → hromada» pipe. Donors (GIZ, U-LEAD,
NEFCO, …) often sit beside the partnership but are a different layer
([donor-programs.md](./donor-programs.md)).

### Core narrative

Win-win: EU municipalities bring institutional / technical practice and
material support; Ukrainian hromadas bring **wartime resilience know-how**
(blackouts, civil protection, continuity of services) that EU peers want to
learn from.

### Typical themes

| Theme | Notes |
|-------|--------|
| Resilience / civil defence / crisis | Strongest post-2022 motivator for EU side |
| Energy | Efficiency, renewables, blackout preparedness (often top in C4C priorities) |
| Education / youth / people-to-people | Schools, exchanges |
| Social | IDPs, veterans, rehab, elderly care |
| Utilities | Water, waste, circular economy |
| Digital / governance | E-services, participatory tools |
| Local economy | SME, investment climate, B2B |
| Cross-border / INTERREG | Western oblasts — adjacent but not the same as twinning |

---

## How a hromada finds a partner

There is **no single marketplace**. Channels we see:

| Channel | Mechanism |
|---------|-----------|
| **SKEW (Germany)** | DE municipality signals interest → SKEW/GIZ matchmaking → contacts, visits, ~250+ DE–UA network |
| **Cities4Cities** | Profile in DB → consultation → shortlist → meetings (Polaris / SALAR International) |
| **Forums** | URC, EURegionsWeek, Nordic–UA forum, DE–UA municipal conferences |
| **Personal ask** | e.g. Poltava: ask for a fire-truck ladder at a forum → path to Kalmar |
| **Associations** | АМУ, VNG, UBC, national local-government associations |

UA side: mayor / deputy / international desk. EU side: municipal leadership +
often municipal NGOs / volunteer networks.

---

## German format (SKEW) — best-documented layer

- Running since **2015**; surge from **2022** as *solidarity partnerships*
  (formal and informal under one umbrella).
- Operator: Servicestelle Kommunen in der Einen Welt (Engagement Global / BMZ),
  with in-Ukraine support (KAS, GIZ).
- Open list + map (HTML; no public CSV/API) — scraped into our release.
- Our coverage (order-of-magnitude): ~179 linked DE–UA edges of ~268 raw;
  ~88 unmatched (raions, Kyiv city, utilities, missing aliases).
- Types in list: mostly `Kommunalpartnerschaft`; also
  `Betreiberpartnerschaft` (utility operators — we skip as non-hromada).
- Policy themes (SKEW): energy efficiency, sustainable urban development, good
  governance; wartime practice adds humanitarian and reconstruction support.
- Many large cities hold **several** German partners at once
  (Lviv, Odesa, Ivano-Frankivsk, Mykolaiv, …).

**Coverage honesty:** German SKEW is still the only *HTML map* registry.
France now has a bulk PDF analogue (AFCCRE, below). SE / PL / others still
appear as Ministry-map rows, cases, and news, not a complete catalogue.
See also «we have not found all partnerships» below.

---

## AFCCRE — French jumelage directory (2026-09-17)

French-side analogue of SKEW. Operator: Association Française du Conseil des
Communes et Régions d'Europe (AFCCRE / CEMR). No public CSV/API — two PDFs:

- [Annuaire des communes jumelées](https://www.afccre.org/sites/default/files/Annuaire%20des%20communes%20jumel%C3%A9es_1.pdf) (snapshot used: 2025-09-02)
- [Nouveaux jumelages 2025](https://www.afccre.org/sites/default/files/Nouveaux%20jumelages%202025.pdf)

`yarn twinning` fetches both into `data/cache/twinning/` (`pypdf` text extract)
and merges `source: afccre` / `confidence: registry` into
`twinning-partners.json`. Aliases: `data/sources/twinning-fr-aliases.json`
(KATOTTG, because Миколаїв / Долина / Городок collide). Cyrillic Ministry FR
rows that are the same commune are tagged `duplicate_of_afccre`
(`twinning-fr-duplicate-pairs.json`, 10 pairs) — not deleted.

**This run:** 63 raw edges → 56 linked / 44 hromadas; 7 skipped (Kyiv city +
districts, Crimea Yalta, Луганськ/Торез without KATOTTG). Occupied TGs that
*have* a KATOTTG stay (Мелітополь, Бердянськ, Маріуполь, Нова Каховка). Two
generations: pre-2022 Soviet-era twins and post-2022 solidarity jumelages.
MEAE/CNCD Atlas was in maintenance (not scraped). Cités Unies France is a
solidarity fund, not a pair registry.

Do **not** set `known: true`. Same weak `social_capital` input as SKEW
(both-sides registry twinning).

---

## Cities4Cities — what it is and is not

- ~100 network partnerships across several EU countries + US (claimed); ~600 UA
  municipalities in the **seeking-partner** database (`markers.json`).
- Integrated here as: (1) news-title pair extraction (hypotheses);
  (2) `c4c_url` = listed in the municipality DB (not a confirmed twin).
- Not a SKEW-like pair registry. Full scrape of all profile free-text for named
  foreign cities is still open work.

---

## Cases worth citing

### Poltava ↔ Kalmar (SE) — clearest format story

Lviv Municipal Partnership Forum (Nov 2023) → request for fire-fighting ladder →
equipment + first contacts (Jan 2024) → visits, generators for utilities/health/
kindergartens → joint work with emergency / health services → sister-city
memorandum at URC 2025. Swedish side explicitly frames learning crisis
preparedness from Poltava; waste management is a next track. In Poltava’s
strategy extract: international agreements present; **classical UA–UA МСС with
neighbours largely absent** — useful product contrast.

### Kamianske ↔ Wuppertal (DE, SKEW, 2025)

Named in the hromada strategy as SKEW twinning. Example of a wartime-era link
already written into the development document.

### Zhytomyr ↔ Kassel (DE)

In SKEW from 2024; C4C narrative of moving from agreement to living partnership
(delegation visit). Public framing: energy efficiency + resilience / blackouts.

### Kherson ↔ Norrköping (SE) + networks

Strategy extract cites Cities4Cities, Baltic Cities (UBC), VNG International.
Emphasis on crisis management, education, economy — typical arc from
humanitarian start toward development tracks.

### Mykolaiv — twinning beside donor infrastructure

German twins (Hannover, Sindelfingen, …) **and** «Mykolaiv–Denmark» + NEFCO
water work / COWI–One Works planning. Shows twinning often coexists with
separate donor infrastructure packages.

---

## Statistics (2026-08-16 snapshot)

Computed by joining `twinning-partners.json` (178 hromadas listed) against
`hromadas.json` demographics (1463 hromadas, join key KATOTTG). **Key split:
of the 178 listed, only 114 have a confirmed partner edge — the other 64 are
Cities4Cities profiles with no confirmed pair yet ("seeking", not "twinned").**
Stats below use the 114-confirmed group unless noted.

### Scale — confirmed-partner hromadas vs baseline

| | Confirmed partner (n=114) | Seeking-only, C4C (n=64) | All hromadas (n=1463) |
|---|---|---|---|
| міська | 86.0% | 45.3% | 27.9% |
| селищна | 8.8% | 32.8% | 29.5% |
| сільська | 5.3% | 21.9% | 42.6% |
| median population | 42,980 | 17,678 | 10,658 |
| mean population | 111,560 | 28,499 | — |

Twinning is a **big-city format**: 4× baseline median population, 86% urban
type. The seeking-only C4C pool is much closer to the overall hromada mix —
large cities convert "seeking" into a real partner far more than small ones.
Largest confirmed: Kharkiv (950,072). Smallest: Esman selyshche hromada
(1,528).

Population buckets, confirmed group (n=114): <5k: 1 · 5–15k: 13 · 15–30k: 22 ·
30–60k: 35 · 60–150k: 21 · 150k+: 21.

### Agreement type / source (194 partner edges total)

| Type | Source | Count | Share |
|---|---|---|---|
| Kommunalpartnerschaft | SKEW (DE registry) | 179 | 92.3% |
| Cities4Cities partnership | C4C news | 11 | 5.7% |
| strategy_mention | hromada strategy text | 4 | 2.1% |

Country: DE 180 (92.8%), unspecified/C4C 11, SE 1, BG 1, PL 1 — confirms the
"German format is the only bulk registry" point above with hard numbers.

### Timing — clear 2022+ solidarity wave

Of 190 dated edges (4 strategy mentions undated): <2015: 30 · 2015–2021: 14 ·
2022: 33 · **2023: 57** · 2024: 30 · 2025+: 26. **76.8% of dated edges start
2022 or later** — a wartime surge layered on a pre-existing (mostly pre-2015)
base, consistent with the "running since 2015, surge from 2022" note above.

### Concentration

- Partners per hromada (n=114): 1 partner 67 · 2: 26 · 3: 15 · 4: 3 · 5+: 3.
  Top: Poltava (7), Ivano-Frankivsk (6), Lviv (5), Zhovkva/Mykolaiv/Odesa (4
  each).
- Oblast twinning rate (confirmed / all hromadas in oblast): Lviv 20.5%
  (15/73), Kyiv obl. 17.4% (12/69), Volyn 13.2%, Poltava 11.7%,
  Ivano-Frankivsk 11.3% — top oblasts by raw count: Lviv (15), Kyiv obl. (12),
  Poltava/Ivano-Frankivsk/Volyn (7 each).
- German *Land* of partner (top): Nordrhein-Westfalen 36, Bayern 27,
  Baden-Württemberg 25, Niedersachsen 22, Hessen 14.

### Caveat

SKEW/C4C/partnership-map still have **no per-edge theme**. The "Typical themes"
table above stays narrative. Counted themes now come from a **separate**
layer: Law 3668-IX registered agreements (`yarn intl-agreements` →
`intl-agreements.json`) plus Interreg keep.eu official `themes[]`. Do not present the
qualitative table as a tally, and do not treat 3668 `theme_ids` as SKEW
twinning themes.

Method: ad hoc analysis, 2026-08-16, not a committed script — rerun by joining
`twinning-partners.json` `.hromadas[]` against `hromadas.json` on
`katottg`/`Katottg`, filtering `partner_count > 0` for the "confirmed" group.

---

## Registered agreements (Law 3668-IX) and Interreg — map overlay (2026-09-16)

Three UA–EU layers stay distinct on `yarn graph-pin-matching`:

| Layer | What | Theme source | Map |
|---|---|---|---|
| Twinning | Sister cities / solidarity | none on the edge | violet nodes; country hubs in Graph |
| **3668 register** | MinRegion-registered international territorial agreements | free-text `сфера` + title → `intl_theme` | card section + «Теми UA–ЄС» filter |
| Interreg | keep.eu projects | official `themes[]` (mapped) + title fallback | cyan nodes if `is_local_authority` |

**EU pairing candidates** on the hromada card are a *revealed-cooperation pool*:
EU places that already appear on a 3668 agreement (or a theme-matched twin)
with some Ukrainian hromada on a shared theme. Not embedding cosine, not
Interreg eligibility, not «AI знайде близнюка». Warm intros (SKEW / JTS /
associations) still required.

Commands: `yarn intl-agreements`, `yarn interreg --offline`, `yarn test-intl-theme`,
then `yarn graph-pin-matching`. Keep.eu official `themes[]` live on each
Interreg partnership (`keep_themes` / mapped `theme_ids`); English titles
only fill gaps (e.g. BCP jargon that keep.eu tagged as Safety/Infrastructure).

---

## Implications for this project

| Domestic МСС matching | UA–EU twinning |
|----------------------|----------------|
| Law 1508-VII, registry PIN | Foreign municipal partners |
| Strategy / geo / network scores | SKEW registry + C4C news + strategy mentions |
| Labels: схожа стратегія / зручний сусід / … | Label: місто-побратим ЄС |
| Hypothesis unless `known: true` | SKEW ≈ registry; C4C news / strategy = hypotheses |

Bottleneck analogy (DOBRE on МСС partner search) partially applies: finding and
warming up a foreign partner is also relational and brokered (SKEW, C4C,
forums) — our matching layer does not replace that brokerage.

### Coverage gaps (do not overclaim)

1. Non-DE EU countries: no SKEW equivalent in our pipeline — **closed
   2026-09-02** via decentralization.ua's Ministry partnership map; France
   additionally got a French-side bulk source **2026-09-17** (AFCCRE PDFs)
2. C4C: news pairs only (~11), not all ~100 claimed partnerships
3. Pre-2022 twinning outside SKEW/C4C: often only on municipal websites
4. Kyiv city / raions / utilities: intentionally skipped
5. Strategy text rarely lists all sister cities by name («28 twin cities»
   without a roster is not expandable)

Commands: `yarn twinning`, `yarn twinning --offline`, map layer via
`yarn graph-pin-matching` (indigo node highlight + card section).

---

## decentralization.ua partnership map — the non-DE gap-filler (2026-09-02)

Separate release: `data/releases/partnership-map.json` (`yarn partnership-map`).
Source: Мінрозвитку's own verified partnership registry, per-hromada pages at
decentralization.ua/newgromada/&lt;id&gt;, resolved by direct **KATOTTG join**
(the page prints the hromada's own KATOTTG — no transliteration needed).
Full details, method, and caveats: [external-data-sources.md](external-data-sources.md#decentralizationua--ministry-partnership-map-all-countries-not-just-de).

**Headline numbers**: 288 hromadas with ≥1 partner, 1134 partner-city rows,
47 partner countries. Poland dominates (464 rows) — far ahead of Germany
(81), Hungary (87), Romania (68). This is the first time this project has
country-level breadth beyond SKEW's DE-only registry.

**Treat as complementary to SKEW/C4C/strategy, not a replacement or
superset** — each layer misses cases the other has (Poltava↔Kalmar, a
documented flagship case above, is absent from the Ministry page;
conversely the Ministry page picks up hundreds of PL/HU/RO/SK pairs SKEW
never could, since SKEW is DE-only). The Ministry's own dashboard
(decentralization.ua/twincities, Tableau-based) claims materially higher
totals (490 hromadas / 2119 agreements / 1740 partners) than the per-hromada
pages we scraped. **Deliberately not scraped further**: that dashboard's
publisher has explicitly disabled Tableau's data-export commands
(`allow_view_underlying: false`, `allow_summary: false` in its own session
config — confirmed 2026-09-02, a fresh `bootstrapSession` returns `410
Gone` on the download-data path) — read as an intentional access control,
not a technical gap to route around, so we stopped there. No per-partner
date or partnership-type field exists in this source, unlike SKEW's "since"
year.

**Merged 2026-09-02** into `twinning-partners.json` (`yarn twinning
--offline` now also reads `partnership-map.json`): the release went from
114 confirmed-partner hromadas to **366**. **AFCCRE fold-in 2026-09-17**
raised that to **372** hromadas (56 FR jumelage rows; 10 Ministry FR rows
tagged `duplicate_of_afccre`). The map/graph (`yarn graph-pin-matching`,
rebuilt 2026-09-17) shows `twinning=370` hromadas across **48 country hub
nodes / 795 edges**. Per-source counts
(`coverage.decentralization_ua_partners_added`
= 1109 of 1134; the other 25 lost to KATOTTG rows twinning-partners.json's
own index doesn't carry) are the trustworthy per-source number.

**Cross-source dedup (2026-09-02)**: non-DE decentralization_ua rows are
additive and need no dedup — SKEW is DE-only, so there is no possible
overlap. DE-country rows are the only overlap risk (94 of 366 hromadas have
entries from both SKEW and decentralization_ua). Checked all 54 DE rows on
those overlapping hromadas via fuzzy string match (`difflib`, transliterated
with the same `to_de()` used for hromada-name resolution) **then manually
verified against real German city names** — a blind ratio threshold isn't
safe here (e.g. decentralization_ua's "Кельн" [Köln/Cologne] scored 0.60
against SKEW's "Kassel" for the same hromada but is a different city).
**38 of the 54 are confirmed real duplicates**, curated in
`data/sources/twinning-de-duplicate-pairs.json` and tagged
`partner.duplicate_of_skew` (the matched SKEW name) at build time — not
deleted, just flagged, so the audit trail stays intact. Use
`hromada.distinct_partner_count` (excludes tagged duplicates), not
`partner_count`, for a non-inflated total. The other 16 looked similar by
crude transliteration but are genuinely different cities (e.g. Kelln/Köln vs
Kassel, Augsburg vs Bedburg) and were left as distinct additional partners.

---

## Manual pairs — non-EU, no bulk registry (2026-09-18)

Some pairs exist with countries that have **no SKEW/AFCCRE/decentralization.ua
analogue** — no bulk registry to scrape, only individual news stories.
Curated by hand into `data/sources/twinning-manual-pairs.json` (keyed by
KATOTTG, verified against `hromadas.json`), merged additively at build time
(`source: "manual"`, `confidence: "news_mention"`).

**Australia (2026-09-18 research)**: searched broadly for AU–UA municipal
partnerships — found only **2 pairs**, both regional/suburban councils, both
grassroots-initiated (not a national program like SKEW):

| Hromada | KATOTTG | AU partner | Since |
|---|---|---|---|
| Лозівська (Харківська обл.) | UA63100050000079487 | Edward River Council (Deniliquin), NSW | 2023-10-17 |
| Бородянська (Київська обл.) | UA32080030000070006 | City of Tea Tree Gully, SA | 2023-05-22 |

Neither pair appears in Wikipedia's twin-town lists for Ukraine or Australia
— same "registry lags reality" pattern as SE/PL. No major Australian metro
(Melbourne, Sydney, Brisbane, Perth) has adopted a Ukrainian sister city;
Melbourne only terminated its St. Petersburg tie (2023-05-30) without a
replacement. Treat this as **not exhaustive** — worth a fresh pass if the
Australia angle becomes relevant again.
