# Draft GitHub issue — KSE-Loc-Data-Hub cross-link

**Target repo:** https://github.com/kse-ua/KSE-Loc-Data-Hub/issues/new  
**Status:** draft only — review and paste manually when ready. Do not auto-submit.

---

## Title

```
Cross-link complementary dataset: hromada strategy-text extractions + МСС candidate hypotheses (join on KATOTTG)
```

---

## Body (copy from here)

### Summary

We maintain a sibling open-data project — **[hromada-strategy-collab](https://github.com/MaxSemenchuk/hromada-strategy-collab)** (W3I / Civic Tech Lab) — that covers the **same 1,469 mainland hromadas** as KSE-Loc-Data-Hub but on a **complementary axis**: LLM-structured extractions from official hromada development-strategy documents, plus pairwise goals-similarity scores as **candidate** inter-municipal cooperation (МСС) hypotheses.

We believe the two datasets are natural complements rather than competitors:

| | **KSE-Loc-Data-Hub** | **hromada-strategy-collab** |
|---|----------------------|----------------------------|
| Core question | Resilience & decentralization covariates | Strategy-text semantics & МСС matchmaking hypotheses |
| Primary output | `full_dataset.csv` (~130 vars) | Structured `Goals`/`Projects`/… + `matching-edges.json` |
| МСС | Existing agreements (`partnerships-hromadas.csv`) | Ranked *candidate* pairs (unverified unless registry-confirmed) |
| Join key | `hromada_code` | `katottg` (same KATOTTG codes) |

Full synergy write-up: [docs/kse-synergy.md](https://github.com/MaxSemenchuk/hromada-strategy-collab/blob/main/docs/kse-synergy.md)

### What we already consume from KSE

At analysis time we lazy-fetch (no CSV copies in our repo):

- `geography.csv` — proximity / frontline signals for weighted matching
- `edem-data.csv` — e-participation maturity (we use the standalone file, **not** edem columns in `full_dataset.csv`, because of the NA→0 imputation in `ellis-general.R`)
- `partnerships-hromadas.csv` — ground-truth validation of our matching method
- `minregion-war-status.csv` — context for missing strategy documents

We attribute KSE via Zenodo [10.5281/zenodo.15267573](https://doi.org/10.5281/zenodo.15267573).

### What we can offer back

- **`data/releases/hromadas.json`** — strategy extractions (`Goals`, `Projects`, `Strengths`, `Challenges`, `PartnersMentioned`, `MSSAgreements`) for ~57 hromadas so far (pilot; scaling toward full corpus)
- **`data/releases/matching-edges.json`** — pairwise goals-cosine scores; edges marked `known: true` align with your `partnerships-hromadas.csv` for method validation; other edges are explicit *hypotheses*, not claims of real agreements
- Documented honest nulls (`SourceQuality = none`) where no strategy PDF could be found

Happy to discuss a lightweight cross-link (README badge, "Related datasets" section, or a row in `data/derived/README.md`) — no merge of repos required.

### Ask

1. **Reciprocal link** — add a pointer to our repo/docs in KSE's README or derived-data README as a complementary text-semantics layer.
2. **Edem missingness note** — if not already planned, a one-line warning in `data/derived/README.md` that `edem_total` in `full_dataset.csv` imputes unscrapeable hromadas as 0 (we found this by reading `ellis-general.R`; happy to PR if useful).
3. **Optional** — if useful for your team: we can share a KATOTTG-indexed export of matching-edge hypotheses restricted to hromadas that appear in your validation samples, or join our extractions into a derived CSV you host.

No action needed if this doesn't fit your roadmap — we wanted to flag overlap early and avoid duplicating covariate work you're already doing well.

### Contact

Max Semenchuk — W3I / Web3 Infrastructure ([w3i.network](https://w3i.network))  
Project docs: https://github.com/MaxSemenchuk/hromada-strategy-collab/tree/main/docs

---

## Labels (suggestion)

`documentation`, `enhancement` (or whatever the KSE repo uses for cross-project links)

## Notes for submitter

- Review pilot coverage numbers before filing (currently ~57 text-mined hromadas) — update the issue body if export has run since draft date.
- Consider @-mentioning maintainers listed in KSE README (e.g. Tymofii Brik / team) if appropriate.
- Keep tone collaborative; KSE is the covariate authority, we are the text-semantics layer.
