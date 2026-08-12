# Sketch: matching hromadas to funding opportunities (2026-08-11)

**Status:** desk sketch only, not scoped as work. Written on request after discussing
whether the existing goals-based matcher could extend from hromada↔hromada
partnerships to hromada↔grant/donor-call. Relates to but is distinct from
[project-strategy-future-backwards.md](project-strategy-future-backwards.md) Brief 3
(EU instrument + validation dataset) — that brief is about matching hromadas to each
other across a border; this is about matching a hromada to a *funder*, which could
land inside any of Brief 1's three product forms.

## Why this is mostly a data problem, not an algorithm problem

The matching engine already exists: [match.py](../scripts/analysis/match.py) scores
hromada-pair similarity from parsed strategy Goals text, and
[mss_suggest.py](../scripts/analysis/mss_suggest.py) classifies those goals into a
controlled theme vocabulary (`THEME_LABELS`: cnap, fire, waste, water, education,
health, social, tourism, culture, utilities, energy, archive, roads, archbud,
registration, agglomeration, security). Extending this to a second node type
(funding opportunity instead of hromada) reuses the same theme classifier and cosine
scoring — the open question is where opportunity data with matchable structure comes
from, since strategy text is stable for years but grant calls open/close on a clock.

Related existing asset, but solving a different problem:
[donor-synergy.json](../data/releases/donor-synergy.manifest.json)
(`donor_synergy.py`) already uses `hromadas.json`'s `DonorsPrograms` field to find
network overlap — but that's *retrospective* ("who already got funded by whom"),
used as a TERGM covariate. What's missing is *prospective* data: open calls, their
eligibility rules, deadlines — nothing in the repo currently tracks that.

## Candidate sources, tiered by fit + effort

**Tier 1 — Ukraine-specific, some already adjacent to this repo:**
- `DonorsPrograms` field in `hromadas.json` — already-tagged donor names (GIZ, USAID
  DOBRE, U-LEAD, UNDP, etc.) are a seed list of *who* funds hromadas; doesn't give
  open-call data, but tells you which funders to go check first.
- DREAM (dream.gov.ua, already integrated via
  [fetch_dream_priorities.py](../scripts/analysis/fetch_dream_priorities.py)) — this
  is a project-pipeline/marketplace registry (hromadas post project ideas seeking
  investors), not a grant-call listing. Worth checking whether its API exposes the
  investor/funder side, not just the revealed-priorities side already pulled.
- Держ. фонд регіонального розвитку (DFRR) competition announcements,
  decentralization.gov.ua grant news, U-LEAD municipal grant components — all
  publish call text but no API; would need scraping, same consolidation-from-scratch
  problem Brief 3 flagged for Polish/Czech strategy text.
- Prozorro / Prozorro.Sale — mostly procurement, not grants; low fit.

**Tier 2 — EU-wide, ties to Brief 3's instrument question:**
- EU Funding & Tenders Portal (ec.europa.eu/info/funding-tenders) — has a real
  search API, covers Interreg/LEADER/EGTC among others. If Brief 3 lands on
  Interreg specifically, this becomes the primary source and the two efforts merge.
- SKEW/C4C twinning program grant lines — already have 178-node twinning-layer data
  in this repo; a twinning *grant call* is a natural extension of an edge that
  already exists.

**Tier 3 — generic aggregators, easiest technically, weakest fit:**
- DevelopmentAid grants database, Fundsforngos, GrantStation — broad NGO/municipal
  grant listings, mostly paywalled or NGO-oriented rather than local-government
  specific; treat as a fallback, not a primary source.

## Proposed schema (if/when built)

A new release, `funding-opportunities.json`, structured like existing releases
(compare `matching-edges.json`, `mss-candidates.json`):

```json
{
  "id": "giz-decentralization-2026-01",
  "funder": "GIZ",
  "program": "U-LEAD with Europe",
  "instrument_type": "grant | twinning | loan | technical_assistance",
  "theme_tags": ["waste", "energy"],
  "eligibility": {
    "oblast_allow": null,
    "population_min": null,
    "population_max": 50000,
    "urban_rural": "any | urban | rural",
    "frontline_status_excluded": true,
    "legal_form_required": null
  },
  "deadline": "2026-03-15",
  "status": "open | closed | rolling",
  "budget_range": [10000, 250000],
  "url": "...",
  "source_quality": "official | aggregator | secondhand",
  "last_checked": "2026-08-11"
}
```

Matching would produce a new edges file (`funding-matches.json`) the same shape as
`matching-edges.json` but with one side being an opportunity id instead of a hromada:
theme overlap from the existing classifier, hard-filtered by `eligibility`, no cosine
score needed since eligibility is closer to boolean gating than similarity.

## The actual tradeoff (why not just build it)

Everything above is cheap to write down and expensive to keep true. Strategy Goals
text is stable for years, which is why the current corpus can be built once and
scored many times. Grant calls have deadlines measured in weeks — a
`funding-opportunities.json` that isn't refreshed on a real cadence goes from useful
to actively misleading (recommending a closed call) faster than any other data in
this repo. That's a different operational commitment than anything the project has
taken on so far, and it's the same capacity question Brief 1 already left open
(who staffs ongoing anything). Concretely: this is worth scoping for real once Brief
1/2 converge on a product form that needs it — building the live feed before that is
the same "two half-finished efforts" hell-risk Brief 1 already named, aimed at a
fourth track instead of a third.

**Recommendation:** keep this document as the parking spot for the idea; the first
real next step, if pursued, is a manual pull of 10-20 real open calls from Tier 1
sources to see whether they even contain enough structured eligibility data to fill
the schema above — before investing in any scraper or API integration.
