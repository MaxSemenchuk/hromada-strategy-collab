# Project strategy — Future Backwards synthesis (2026-08-10)

**Purpose:** canonical strategic reference for `hromada-strategy-collab`, built with
[Liberating Structures "Future Backwards"](https://www.liberatingstructures.com/8-future-backwards/)
(Было · Сейчас · Рай · Ад → backcast). Distinct from
[docs/project-history.md](../docs/project-history.md) (methodology chronicle) and
[docs/research-questions.md](../docs/research-questions.md) (open research questions):
this document is about product/funding direction, not method. Update it when a
listed decision gets made — see [Decisions log](#decisions-log) at the bottom.

## Было (history)

- Started as civic-tech hackathons for Мінцифра in the Plurality / RadicalxChange
  vein.
- KSE deliberative-democracy consultation redirected the focus down a level: from
  ministry CDTO to **hromada-level CDTO**, with ministry CDTO / Мінцифра itself
  possibly still relevant for balance.
- Thesis at the time: value to МЦ/CDTO requires sourcing hackathon challenges
  *from* them.
- МЦ builds universal digital-democracy tools (e.g. petitions) but is open to
  complementary solutions; some hromadas already run custom IT (e.g. tax
  systems).
- Open concern, never resolved: CDTO capacity in small/rural hromadas may be too
  low to produce good challenges unprompted.
- Funding aimed at EU sources; earlier cooperation with Binance also existed.
- **What this document adds:** the current project (below) is not a separate
  track — it's a second pivot away from the same fork. The unresolved CDTO-
  capacity concern above has a direct answer in the "Рай" section: don't ask
  small-hromada CDTOs to invent challenges, mine the challenges out of their
  strategy text instead.

## Сейчас (present) — as of 2026-08-10

What was in the working note, plus what the repo already contains that hadn't
surfaced yet:

- 300+ hromada strategies collected and structured
  (`data/releases/hromadas.json`), candidate matches computed
  (`matching-edges*.json`), but IT-specific asks inside those matches are not
  yet obviously separable from general cooperation asks.
- **TERGM pilot already validates part of the mechanism**, not just "found some
  matches": on 316 tie-formation events, `geo_score` is a confirmed predictor
  (tight CI) and `donor_overlap` is tentatively confirmed. `goals_cosine` and
  the transitivity/"bridge" signal are *not* confirmed yet — do not let a pitch
  imply otherwise. Full detail: project memory
  `project_mss-tergm-pilot-findings.md` / `internal/tergm-pilot-results.json`.
- **Tkachuk's (ІГС) practitioner correction is the load-bearing theory of
  change**: the tool does not replace trust between hromada heads (60–90% of
  deals still go through personal contact) — it lowers transaction costs /
  uncertainty and surfaces mutual benefit. Every downstream pitch (hackathon,
  matchmaking, EU) should be framed this way, not as "AI finds your partners
  for you." See `.cursor/rules/hromada-project.mdc` hard rule 9.
- **A draft EU-instrument pivot already exists**
  ([internal/eu-transfer-one-pager.md](eu-transfer-one-pager.md)): reposition as
  a system for EU cooperation instruments (Interreg looks structurally closest
  to Law 1508 МСС), with the Ukraine rollout as the *validation experiment*,
  not the target market. It explicitly flags its own risk: without picking one
  instrument + a validation dataset first, this reads as grant-chasing
  repackaging to any funder who's seen that move before.
- **A product decision has been open since 2026-08-03 and is still unresolved**:
  open-data vs matchmaking vs W3I-internal
  ([docs/project-history.md § Open threads](../docs/project-history.md#open-threads-as-of-2026-08-03)).
  This is, concretely, what "нужно понять как двигаться далее" means — it's not
  a new question, it's the same question that's been sitting open for a week.
  See [Decisions log](#decisions-log).
- **The IT-request ambiguity has a named cause**: predictive validity hasn't
  been tested. The model currently does retrospective pattern-matching on
  already-known pairs; whether `score` (or `explicit-ask` text) has forward
  predictive power is an open research question, not yet answered
  ([docs/research-questions.md §1](../docs/research-questions.md#1-predictive-validity-method-is-currently-retrospective-only)).
  Sharpening IT-asks specifically may need the same forward-test treatment,
  scoped to IT/digital-solution asks in the corpus.
- A paper is in progress (`internal/paper-draft-tergm-mss.md`). Taraktaş and
  Сердюк are locked in as co-authors (no conflict). Ткачук is pending, not
  locked — see [Decisions log](#decisions-log): the plan is to ask him
  directly whether he consents to co-authorship rather than the project
  deciding unilaterally, since `.cursor/rules/hromada-project.mdc` treats him
  as a consulted-expert-only by default and that's the fallback if he
  declines or doesn't respond by submission.

## Рай (heaven)

What was in the working note, plus what should be added given the above:

- Funded programme matching hromadas + IT/cooperation projects — **specifically
  anchored to one named EU instrument** (Interreg first candidate) with a real
  validation dataset behind it, not "EU funding" in the abstract.
- Many МСС collaborations result, **and** the forward-test confirms the model
  had genuine predictive power, not just retrospective pattern-matching — this
  is the difference between "useful" and "would have happened anyway."
- Better democracy + EU integration outcomes.
- Strong scientific contribution + collaboration, with a path to actual EU
  implementation, not just citation.
- **Original hackathon vision resurrected on firmer ground**: Мінцифра/CDTO
  challenges sourced from explicit-ask + template-collision signals mined out
  of strategy text, not invented by CDTO staff — directly answers the "Было"
  concern about weak CDTO capacity in small hromadas without requiring them to
  get more sophisticated first.
- Template-collision (shared consulting template as a capacity signal) matures
  into a diagnostic donors can use to prioritize capacity-building, not just a
  matching-pipeline flag.

## Ад (hell)

What was in the working note, plus what should be added:

- ОТГ don't respond to outreach — **this is a testable, gate-able risk**, not
  just a fear: the first real outreach batch
  (`internal/outreach-messages.md`) should be run and read as a go/no-go
  signal, not routine busywork.
- Matching is useless — **specifically**: predictive-validity forward-test
  comes back null, meaning the model only describes what already happened.
- No funder interest / no funding.
- Weak science / credible criticism — **specifically named failure mode**:
  pitching the EU-instrument reframing without first naming the instrument and
  validation dataset reads as opportunistic repackaging of a Ukraine project,
  not a new system (the one-pager's own stated risk).
- **Added risks not in the working note:**
  - Product indecision becomes permanent — the open-data/matchmaking/internal
    decision never gets made, and the project drifts as a research artifact
    with no operational owner.
  - Data goes stale faster than the pipeline updates: frozen elections have
    produced *sticky heads* now, but a future round of local elections could
    produce mass head turnover ("fragile heads"), decoupling strategy text and
    known-pair networks from current reality.
  - Publishing pair recommendations reads as intrusive or politically awkward
    rather than helpful, especially where resource asymmetry between a
    recommended pair is visible to everyone.
  - Two half-finished efforts instead of one finished one: chasing the EU
    pivot and the domestic hackathon/CDTO track simultaneously without
    sequencing drains the same limited attention.

## Backcast — what this implies now

In rough priority order, because several of these gate everything downstream.
The top three are detailed in full below ([Decision briefs](#decision-briefs));
the rest are one-liners because they don't need the same depth yet.

1. **Product form** — open-data vs matchmaking vs W3I-internal. Open since
   2026-08-03, blocks a coherent answer to "as CDTO/МЦ, what do I do with
   this." → [Brief 1](#brief-1-product-form).
2. **Predictive-validity forward-test** before any funder pitch — the fact
   separating "Рай" from "Ад." → [Brief 2](#brief-2-predictive-validity-forward-test).
3. **EU instrument + validation dataset**, named before pitching, not left as
   "candidate." → [Brief 3](#brief-3-eu-instrument--validation-dataset).
4. **Treat the first outreach batch as a go/no-go experiment**, with an
   explicit response-rate threshold decided in advance, not just "send and
   see."
5. **Co-authorship — resolved as pending, not locked (2026-08-10).** Taraktaş
   and Сердюк are locked in as co-authors. Ткачук stays pending: the plan is
   to ask him directly whether he consents, rather than the project deciding
   unilaterally — `.cursor/rules/hromada-project.mdc`'s consulted-expert-only
   default is the fallback if he declines or doesn't answer by submission.
   Full resolution note lives in Claude Code project memory
   (`project_paper-coauthors-consultants`), not in this repo.
6. **Sequence, don't parallelize, the EU pivot and the domestic
   hackathon/CDTO revival** — pick which one gets primary attention next, and
   treat the other as a later phase informed by the first, per the "Рай"
   framing above (challenges sourced from mined text, not invented). Brief 3
   below argues this should come *after* Brief 2, specifically.

## Decision briefs

### Brief 1: product form

**The three options, spelled out** (inferred from repo state — confirm with
Max before treating as settled definitions):

- **Open-data**: publish the corpus + candidate-pair hypotheses as a public
  good — largely already true (CC BY 4.0 releases, GitHub Pages stakeholder
  site). No active facilitation. Value = dataset + method available for
  donors, researchers, Мінцифра, or other tools to build on. Low ongoing
  operational load. Success = usage / citations / forks / downstream
  adoption, not deals signed.
- **Matchmaking**: active facilitation — someone uses the candidate list to
  broker actual warm intros between hromadas (per Tkachuk: motivation +
  warm-intro path via ВА ОТГ / ВАГ), plausibly under a funded programme.
  Needs ongoing operational capacity: outreach, relationship tracking,
  corpus refresh. Success = agreements signed, or at minimum first-contact
  meetings held.
- **W3I-internal**: keep it as an internal tool serving W3I's own hromada
  engagements, not a public product. Lowest external/political exposure, but
  caps external impact and forgoes the funder/community narrative the other
  two options are already halfway built for (stakeholder site, outreach
  drafts, TERGM validation).

These aren't permanently exclusive, but the pitch materials currently gesture
at all three at once, which is the actual problem — a funder can't be told
the product is a dataset, a service, and an internal tool simultaneously.

**What's needed to actually decide**:
- Whether "first stakeholder conversations" (named in the original open
  thread as the trigger for this decision) have happened yet. If not, that
  conversation is the real next action — not more internal deliberation.
- Operational capacity check: is there staffing/bandwidth for ongoing
  matchmaking, or does current capacity only support building + publishing?
- Funder alignment: which of the three maps to what the EU instrument in
  Brief 3 actually funds — a data-publishing outcome, a facilitation-service
  outcome, or neither?

**Decision axes**:
1. Operational capacity (can anyone actually staff ongoing facilitation?)
2. Funder alignment (does the target instrument fund a service, a dataset, or
   neither?)
3. Risk exposure (matchmaking inherits the "ОТГ don't respond" hell-risk
   directly; open-data doesn't; W3I-internal avoids it entirely but forgoes
   external credit too)

**Lean**: given Tkachuk's finding (trust matters, tool lowers uncertainty but
doesn't replace relationships — hard rule 9) and Brief 2's unresolved
predictive-validity question, the lower-risk sequencing is **open-data now,
matchmaking as a small funded pilot on a handful of pairs later** — not a
full-programme commitment before Brief 2 has an answer. Pure W3I-internal
gives up ground already paid for (site, outreach drafts, TERGM validation)
without a hard capacity reason forcing that choice.

**Owner / next step**: Max, informed by whichever stakeholder conversations
have actually happened so far.

### Brief 2: does active matchmaking create agreements

**Reframed 2026-08-11** (was: "predictive-validity forward-test"). Max's
correction: with only 56 real agreements total, a passive forecast test can't
carry much statistical weight either way — the more useful question is not
"does `score` predict what would have happened anyway" but "does *actively*
introducing model-selected pairs produce more agreements than would happen
without that push." That's a causal/interventional question, not an
observational one, and the project already has a design for exactly this
sitting unused:
[internal/aim-cc-field-experiment-prereg.md](aim-cc-field-experiment-prereg.md).
It was previously cited in this brief only as "a model for pre-registration
discipline" — it is actually the experiment that answers the reframed
question, not just a style guide.

**Why the existing AIM-CC design already fits**:
- Three arms, all **actively facilitated** (not observed): thematic-matched
  pairs (A), geo-matched pairs (B), random control (C) all get an outreach
  message proposing an intro — this *is* matchmaking, not measurement of
  what pairs would have found each other unprompted.
- The pre-registered **primary outcome is reply-within-21-days**, not
  "agreement signed" — the design already treats agreement-signing as too
  rare to power on directly. Signing / new registry entry is outcome #5 on
  the ordered ladder (§6), explicitly **exploratory, 12-month horizon**, not
  the thing significance is computed on. This matches Max's point: agreements
  are too rare to test *prediction* against, but a facilitated-outreach
  funnel (reply → call scheduled → call held → next step → [exploratory]
  signed) is measurable at pilot scale (24–60 pairs, §4).
- The design is explicit about being underpowered for small effects
  (§4) — feasibility + effect-size estimate is the honest goal of a first
  run, not a definitive policy claim.

**What this means for next steps**: treat launching (or lightly updating)
the AIM-CC pilot as Brief 2's actual next action, not a new T0-split
research task. This also closes the loop with
[Brief 1](#brief-1-product-form): the AIM-CC pilot *is* the "small funded
matchmaking pilot" that brief's lean pointed at, so Brief 1 and Brief 2
resolve into the same piece of work rather than two separate ones.

**Deprioritized, not deleted — the passive forward-test**: the original T0
pre/post forecast design (score all pairs on pre-T0 signals only, check
whether pre-T0-top-ranked pairs disproportionately signed post-T0, vs a
geo-only/random baseline) still has some value as a cheap desk-check before
spending outreach effort — it costs no fieldwork, only re-scoring already
collected data — but should not be treated as the load-bearing validation
step anymore. If run, same constraints as before apply: reason in
**register_number** counts (56 real agreements, not 316 pairwise ties, since
two cliques of 19 and 13 parties explode into up to 171 pairwise rows each),
and confirm the KSE registry
(`data/cache/kse/partnerships-hromadas-network.csv`) has enough date spread
across those 56 to support a non-degenerate split before treating it as a
real design question rather than a data-availability one.

**Owner / next step**: Max decides whether to run the AIM-CC pilot as
currently pre-registered or revise it first; a scoped
data-science/outreach task on `experiment/tergm-pilot` (or a follow-on
branch) executes it. The passive forward-test, if still wanted as a
cheap secondary check, is a smaller side task on the same branch.

### Brief 3: EU instrument + validation dataset

**Decide, don't leave as "candidate"**: `internal/eu-transfer-one-pager.md`
already names Interreg as the lead candidate (funded, multi-year,
application-based, structurally closest to Law 1508 МСС), with LEADER, EGTC,
and twinning (SKEW/C4C) as alternates. This needs to become one instrument on
a date, not a running list.

**The prior, sharper question the one-pager already flags**: this is not one
decision but two — which EU *instrument*, and which *product*:
(a) matching EU municipalities to each other (a new market, no existing
bridge dataset), or
(b) matching UA hromadas to EU twinning/funding partners by extending the
existing 178-node UA–EU twinning layer (SKEW/C4C data already collected).

**New evidence that sharpens this (2026-08-10 cross-tab of the twinning layer
against the domestic МСС network)**: (b) is not just "closer to shovel-ready"
in the abstract — it is concretely a **different market segment**, not a
resize of the same one:
- EU-twinned hromadas skew big/urban (median population 46,533, 87.6%
  «міська»); domestic МСС-network hromadas skew small/rural (median
  population 12,178, only 37.9% «міська»). Porting the matching *engine*
  wholesale to (a) would be applying weights tuned on small-rural dynamics to
  a structurally different actor type.
- Theme overlap between the two layers is thin: domestic МСС candidates are
  dominated by tourism/clusters, ЦНАП/admin services, waste management;
  EU-twinning priorities are energy (near-absent domestically), civil
  defence/resilience, education/youth (almost zero domestically). Only
  waste/environment and civil-defence conceptually overlap.
- GIZ is the donor bridge between the two worlds (79% of GIZ-tagged hromadas
  also have a confirmed EU twin, ~10x enrichment vs baseline) — a concrete,
  named channel if pursuing (b).
- Institutional capacity correlates across both layers (44% of curated
  domestic МСС hromadas also have a confirmed EU twin, vs 7.7% base rate,
  ~5-6x enrichment) — general cooperation capacity, not domain-specific,
  which is a supporting argument *for* (b) even though the specific themes
  don't overlap much.
- Caveat: twinning coverage is 179/194 Germany-only (SKEW registry) — do not
  overclaim breadth beyond DE when using this as the validation base.

This means (b) needs its **own calibration**, not a copy of `match.py` v7.1's
weights — geo/goals-cosine tuned for small-rural domestic pairs won't
transfer cleanly to big-city, energy/education-themed EU twinning — but it
reuses existing data rather than requiring a new EU-side agreement registry
from scratch, which (a) would need for its own version of the "found a real
agreement without being told" proof point (the Ніжин–Батурин–Козелець case
domestically).

**Recommendation**: pursue (b) first — extend the twinning layer — precisely
because the validation dataset problem is already half-solved (176-178 known
partner edges to test against) where (a) has none yet. Treat (a), full EU
municipality-to-municipality matching, as a later phase gated on (b)'s
results, not a parallel opening bid.

**Sequencing dependency**: this decision should come *after* Brief 2, not
before. If predictive validity is unconfirmed on the Ukraine data the model
was built and tuned on, porting the pitch to Europe before that's settled
compounds the "opportunistic repackaging" risk the one-pager itself names,
rather than mitigating it.

**Owner / next step**: Max + whoever holds the EU/funder relationship decides
instrument + product framing (a vs b); a research task then confirms the
concrete validation dataset for whichever is chosen.

**Country candidates for a strategy-text corpus (desk research, 2026-08-11)**:
independent of the instrument/product decision above, checked whether EU
hromadas even publish comparable strategy text — the raw-material question
behind `internal/eu-transfer-one-pager.md`'s "Ukraine-specific plumbing" item
1 (наказ №265 has no EU-wide equivalent, 27 national planning traditions).
Three candidates, ranked by structural closeness to the наказ №265 setup:

1. **Poland** — closest structural match. `strategia rozwoju gminy` becomes a
   *statutory* obligation for every gmina from 2026 (was factultative before;
   exact effective date has conflicting sources — 1 Jan vs 1 Jul 2026, confirm
   against the actual nowelizacja text before relying on it), unless covered
   by a joint `strategia rozwoju ponadlokalnego` (multi-gmina strategy — a
   possible real-world analog to the multi-party-cluster question in
   [docs/research-questions.md §3](../docs/research-questions.md#3-multi-party-clusters-method-is-currently-pairwise-only)).
   Required content (diagnoza → cele strategiczne SMART → kierunki działań →
   wskaźniki → OSI) maps closely onto what `match.py` already extracts from
   наказ №265 text — the extraction method likely ports with a language-model
   swap, not a redesign. Coverage: ~82% of gminas have or are drafting one
   (source dated 2020, treat as directional not current). **Gap**: no central
   registry — publication is per-gmina on individual BIP sites, so porting
   here means repeating the `hromadas.json` corpus-consolidation effort
   (~2,477 gminas) from scratch, not querying an existing aggregator.
2. **Germany** — `Integriertes Stadtentwicklungskonzept` (ISEK), but gated on
   funding applications (Städtebauförderung/EFRE), not a universal legal
   duty — coverage tracks which cities seek that funding, not all
   municipalities. Notable overlap with
   [[project_eu-twinning-vs-domestic-mss-comparison]]: Germany already
   surfaced there as the UA–EU twinning donor bridge (GIZ/SKEW) — this is a
   second, independent reason Germany keeps coming up, via a different
   mechanism (ISEK funding gate, not twinning).
3. **Czech Republic** — `plán rozvoje obce` has a legal basis (zákon
   128/2000 Sb.) and is meant to be public, but no confirmed central
   repository found — likely scattered per-obec, same consolidation problem
   as Poland but with a weaker/less specific legal mandate on content.

**What this does and doesn't resolve**: this identifies *where obtainable
strategy text exists*, not a validation dataset — none of the three has a
KSE-PIN-registry equivalent (a ready list of confirmed cooperation
agreements to test matches against). That gap, not raw-text availability, is
still the harder blocker for either product option (a) or (b) above. Treat
Poland as the lead candidate if/when a raw-corpus-building phase is
scoped, but this doesn't change the Brief 3 recommendation or sequencing —
it's a data-source note for whichever instrument/product gets picked, filed
here so it doesn't get re-derived later.

## Decisions log

Append an entry here whenever one of the above gets decided — keep it short
(what was decided, when, why) rather than re-deriving this whole doc later.

- **2026-08-10 — co-authorship (Brief 5 / item 5)**: Taraktaş and Сердюк
  locked in as paper co-authors, no conflict. Ткачук kept pending rather than
  decided unilaterally either way — plan is to ask him directly whether he
  consents to co-authorship; falls back to consulted-expert-only (per
  `.cursor/rules/hromada-project.mdc`) if he declines or doesn't respond by
  submission.
- **2026-08-11 — product form (Brief 1), reframed as a funding-model
  question**: Max's answer wasn't open-data vs matchmaking vs internal
  directly — it was which *funding form* the product takes: (1) standalone
  research, (2) embedded in a funded programme (Interreg/EGAP-type), or (3)
  self-funded/no external money. Lean: **(2), conditional on Brief 2**
  (matchmaking pilot showing traction) — raising money for a standalone
  Ukraine-only research experiment across ~1,500 hromadas isn't judged
  worthwhile as an isolated step; it only makes sense wrapped in a real
  programme/EU instrument. This converges with the existing Brief 1 lean
  (open-data now, small funded matchmaking pilot later — see
  [Brief 1](#brief-1-product-form)) and with Brief 3's sequencing (EU
  instrument decision comes after Brief 2, not before). No file/code changes
  needed beyond this log entry — the underlying lean was already compatible.
