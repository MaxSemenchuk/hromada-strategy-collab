# Domain generalization analysis — beyond hromadas (2026-08-13)

**Status:** exploratory analysis, not a method or product change. Written to
answer "could this method work for universities/GitHub/etc." with an actual
framework instead of a hand-wave, and to log it for later (e.g. if a
generalizability section is useful for the paper, or if the project ever
needs a side-market to pitch alongside the domestic МСС work). Does not
modify `match.py`, [aim-cc-field-experiment-prereg.md](aim-cc-field-experiment-prereg.md),
or any Decision brief in
[project-strategy-future-backwards.md](project-strategy-future-backwards.md) —
if anything below ever becomes an actual decision, it belongs there, not
here.

## 1. What the method actually is — three pillars, not a formula

`match.py` v7.1's visible formula (60% goals_cosine + 25% geo + 15%
mss_network_score) makes geo look like a co-equal signal with text and
network. It isn't. Geo is a **case-specific adaptation slot**, not a fourth
pillar — it exists because we lack a direct measurement of repeated-contact
history between hromada heads, and physical proximity is the available
proxy for it (shared rayon meetings, admin contact — see
[game-theory-framing.md §2](game-theory-framing.md), Arm B). It plugs a data
gap; it isn't part of what makes the method generalizable.

The actual transferable method is three pillars:

1. **LLM analysis of strategy text** — extracts `a`, the real size of
   potential joint benefit: goals_cosine (DF-weighted bipartite + centroid
   blend), strategic/operational sub-goal split, explicit-ask detection.
2. **Network analysis** — extracts P(other cooperates): existing
   partnership graph (`mss_network_score`), donor/donor-program overlap
   (`donor_synergy.py`), hub-structure risk mitigation. Geo is only used
   where this pillar's real data is sparse.
3. **Game theory** — formalizes what 1+2 feed into. For hromadas this is a
   **Stag Hunt / assurance game** ([game-theory-framing.md §1](game-theory-framing.md)):
   symmetric partners, mutual risk of "being the sucker," tool moves belief
   about the other's move rather than the underlying payoff.

**Key finding from this pass**: Pillar 3 is the one that does *not*
mechanically port. Stag Hunt is the right game for symmetric partners
deciding whether to invest in shared infrastructure — it is not the right
game everywhere. Some target domains are screening games (asymmetric
information), some are public-goods/free-rider games (many-sided, not
pairwise). Treating "the method" as "find a Stag Hunt in domain X" would be
mis-applying it in at least half the domains below. The real transferable
skill is picking the *correct* game per domain, not reusing one.

## 2. Domain comparison

| Domain | Pillar 1 (LLM signal) | Pillar 2 (network signal — real, not a geo-proxy) | Pillar 3 (game form) | Adaptation-slot filler (replaces geo) |
|---|---|---|---|---|
| Universities / research labs | grant abstracts, faculty bios, explicit "seeking collaborators" language | co-authorship graph (OpenAlex/DBLP) — already rich, no proxy needed | Stag Hunt at the "should we talk" stage; Prisoner's-Dilemma-like credit-sharing once collaborating | not needed — network is direct |
| GitHub / OSS | README/roadmap text, "help wanted" issues (cleanest explicit-ask signal of any domain) | dependency graph + contributor overlap — already rich | Public-goods / free-rider game, not pairwise Stag Hunt | tech-stack / release-cadence compatibility |
| Grantmakers ↔ recipients | grant call vs. mission statement — same text genre as hromada strategies | historical funder–recipient graph (Candid) — already rich | **Screening/signaling game** (asymmetric information), not Stag Hunt | funder's programmatic/regional mandate |
| City twinning / municipal diplomacy | development strategies — near 1:1 with current corpus | twinning registries (Sister Cities Intl., SKEW) — sparse, similar to domestic МСС | Stag Hunt + an added diplomatic sign-off cost term (`c_i`) | development-stage / EU-accession-track similarity, not physical distance |
| NGO / civil-society coalitions | theory-of-change documents | coalition-membership data — sparse | Closer to Prisoner's Dilemma (competing for the same donor pool) than Stag Hunt | target-beneficiary-population overlap |
| Startups / accelerators (co-founder or partnership matching) | pitch decks / product descriptions | cap-table / investor-overlap (Crunchbase) — already rich, and *is* the donor-overlap signal directly | Cleanest Stag Hunt outside hromadas (co-founder trust) | not needed — investor overlap is direct |

## 3. Attractiveness scoring

| Domain | Scientific | Impact | Commercial |
|---|---|---|---|
| Universities | **High** — public ground truth (OpenAlex) lets accuracy get checked without building a new dataset from scratch; clean paper angle ("does explicit-ask + thematic matching increase novel cross-lab collaboration") | Medium — value is diffuse and long-horizon vs. a concrete shared ЦНАП saving money | Medium — "academic LinkedIn" plays have historically failed (ResearchGate); a narrower B2B sell to university grant offices is more plausible |
| GitHub / OSS | Medium — data is the richest of all domains but also the most already-mined (MSR community); novelty would have to come from the game-theoretic framing, not the data | Medium — reduces duplicated effort, but maintainer time is exactly the scarce resource (`c_i`) that makes adoption hard | Low–Medium — GitHub/Socket/Snyk occupy adjacent niches; no clear payer for a "should we merge" matcher |
| Grantmakers ↔ recipients | **High** — the game form genuinely differs (screening, not Stag Hunt), which is a more interesting theoretical contribution than a straight port | **High** — misallocated philanthropic capital is a well-documented problem; better matching moves real money to better-fit orgs | **Highest** — Candid, Instrumentl, Submittable already monetize this; proven willingness to pay on both sides |
| City twinning | Medium — harder sample access (multi-country ethics/logistics), but design replicates cleanly | Medium — twinning is often more symbolic than domestic МСС's hard budget savings | Low — not a funded market; a grant-funded pilot, not a product |
| NGO coalitions | Medium — closest analog domain, easy to replicate the AIM-CC design, but little that's genuinely new | Medium–High — coalition efficiency has real downstream effects on advocacy outcomes in an under-tooled sector | Low — nonprofits classically don't pay for tools; would need a donor-funded model, not self-sustaining SaaS |
| Startups / accelerators | Low–Medium — already heavily productized (YC matching, Cofounders Lab); hard to claim novelty | Low–Medium — individual startup outcomes are high-variance and hard to attribute to matching quality | Medium–High — proven market but crowded, and VCs guard deal flow rather than buying a third-party matcher |

## 4. Recommendation (as of this analysis, not a decision)

- **If the goal is strengthening the paper's generalizability claim**:
  universities — cheapest path, because OpenAlex/DBLP co-authorship data is
  public ground truth; no new corpus-building phase needed.
- **If the goal is a commercially viable side-product or pivot**:
  grantmakers ↔ recipients — the only domain scoring high on all three axes,
  and the only one where competitors' existing revenue proves a budget line
  already exists to sell into.
- **If the goal is the smallest rework of Pillar 3**: city twinning — same
  game (Stag Hunt), same text genre, one new parameter (`c_i` diplomatic
  sign-off cost).

None of this changes Brief 1/2/3's sequencing in
[project-strategy-future-backwards.md](project-strategy-future-backwards.md)
— Brief 2 (does active matchmaking create agreements) still gates everything,
including whether *any* of the above is worth pursuing before that question
has an answer.
