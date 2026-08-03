# Idea: university cooperation candidates (same product class as МСС)

Parked 2026-07-31. Not in scope for the current hromada pilot — adjacent
spin-out / reuse of the **agreement-candidate** framing.

## Thesis

The hard step in inter-university collaboration is often **partner search &
framing** (who · about what · which instrument), not the MoU template.
Same class of product as this repo: surface **candidate agreements** with
evidence chips, not a single «similarity score».

Reuse the thinking (`signals[]` / `package` / `known: true` only from
registry-confirmed pairs). Do **not** reuse hromada geo weights or Law
1508-VII forms as-is.

## Mapping

| Hromada / МСС | Universities |
|---|---|
| Hromada | University / faculty / research group |
| Development strategy | Strategy · research agenda · intl office programme |
| Five Law 1508-VII forms | MoU · dual degree · joint programme · research consortium · mobility (Erasmus) · joint lab/centre |
| МСС registry = ground truth | Erasmus+ / Horizon / CORDIS · published MoU lists · existing consortia |
| DOBRE bottleneck: partner search | Same bottleneck for intl offices & research offices |
| Discovery signals ≠ legal form | «similar themes» ≠ dual degree |

Product unit again: **candidate project/agreement** (pair · theme · form) +
`signals[]`. Combined rank is internal; UI leads with package + evidence.

## Signals (sketch)

Keep layers separate (do not fold packaging into one score):

1. **Thematic** — research/strategy theme cosine (faculty- or group-level when possible)
2. **Complementary** — capability ↔ need (lab / students / field sites / accreditation gaps)
3. **Explicit-ask** — partnership language in strategies, calls, intl pages
4. **Existing network** — shared Erasmus KA / Horizon / prior MoU topology
5. **Geo** — weak / optional (mobility corridors, language, accreditation matter more than adjacency)

## What transfers vs what must change

**Transfers:** candidate packing; signal/evidence chips; `known` only from
confirmed partnerships; complementary > pure similarity; validation against
known pairs.

**Must redesign:** atomic unit (faculty/group, not brand only); multi-party
consortia; form taxonomy; data sources (no single «МСС registry»); drop
neighbourhood-heavy scoring.

## Minimal pilot (if ever)

1. Corpus ~30–50 UA (+ optional EU) HEIs with strategy / intl / research text.
2. Form dictionary: MoU · dual degree · joint programme · research consortium · mobility.
3. Separate signal layers as above; UI = package + chips.
4. Regression on known partnerships (analogue of `yarn test-known-pairs`).

## Status

Idea only. No scripts, schema, or release work. Parent product remains
hromada МСС candidates in this repo.
