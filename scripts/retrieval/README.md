# Retrieval batch workflow

Scale strategy extraction beyond the current ~57-hromada pilot without
burning 60–150k agent tokens per hromada on anti-bot retrieval.

## Pipeline

```
1. yarn ckan-search --out scripts/retrieval/ckan-candidates.json
2. Pick URLs → add rows to batch-queue.json
3. yarn download-raw             # PDF/DOC → scripts/retrieval/raw/ (gitignored)
4. Extract text from raw/ → *.extracted.txt / *.groq.txt; set raw_text_path
5. yarn structure-hromada --name "..." --input raw/....txt --write
6. yarn export-hromadas          # refresh data/releases/hromadas.json
7. yarn match && yarn export-matching-edges
```

Local raw files are a **cache for re-analysis** (alternate extractors, full-text
embeddings, audit) — not part of the public `data/releases/` dataset. Commit
URLs + queue metadata only.

## CKAN search

```bash
yarn ckan-search                              # stdout
yarn ckan-search --out scripts/retrieval/ckan-candidates.json
yarn ckan-search --limit 10                   # smoke test
```

API: [data.gov.ua CKAN](https://data.gov.ua/api/3/action/package_search),
CC BY 4.0.

## Batch queue

Edit [batch-queue.json](batch-queue.json):

```json
{
  "name": "Ніжинська міська територіальна громада",
  "katottg": "UA21100090000012128",
  "status": "pending",
  "strategy_url": "https://...",
  "raw_source_path": "scripts/retrieval/raw/nizhyn.pdf",
  "raw_text_path": "scripts/retrieval/raw/nizhyn.extracted.txt",
  "notes": ""
}
```

Status values: `pending` | `downloaded` | `structured` | `failed` | `no_strategy`

## Download raw sources

```bash
yarn download-raw                  # status=pending with strategy_url
yarn download-raw --all            # every row with strategy_url (skip existing)
yarn download-raw --force          # re-download
yarn download-raw --dry-run
```

Writes binaries under `scripts/retrieval/raw/`, sets `raw_source_path`, and
appends sha256 metadata to `raw/manifest.json`.

## МСС registry (ground truth)

```bash
yarn fetch-mss-registry            # → data/cache/mss/mss_registry.xlsx
yarn fetch-mss-registry --force    # refresh from CKAN
```

Official registry of inter-municipal cooperation agreements
([data.gov.ua `912c1ea4-…`](https://data.gov.ua/dataset/912c1ea4-38ea-4648-8306-59fc1df8b51b),
CC BY 4.0). Tabular XLSX — not individual contract PDFs. Cached under
`data/cache/` (gitignored), same pattern as KSE covariates.

## Batch runner

```bash
./scripts/retrieval/run-batch.sh
```

Processes queue entries with `status=downloaded` through
`yarn structure-hromada --write`. Requires `GROQ_API_KEY` and NocoDB
credentials in `.env`.

## Cost notes

- **Retrieval** (finding URLs, fighting Cloudflare): still mostly manual or
  agent-assisted — CKAN covers ~123 datasets, not full coverage.
- **Structuring** (raw text → JSON): offload to Groq (`llama-3.3-70b`,
  free) via `structure-hromada-strategy.ts` — do not run in main agent loop.

## Target

Pilot batch: +10–20 hromadas from CKAN hits with clear PDF links.
Next milestone: 150 text-mined hromadas for meaningful graph validation.
