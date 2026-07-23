# Retrieval batch workflow

Scale strategy extraction beyond the current ~57-hromada pilot without
burning 60–150k agent tokens per hromada on anti-bot retrieval.

## Pipeline

```
1. yarn ckan-search --out scripts/retrieval/ckan-candidates.json
2. Pick URLs → add rows to batch-queue.json
3. Download raw text (PDF/DOC/HTML) → scripts/retrieval/raw/
4. Agent structures the raw text into JSON in-session → yarn structure-hromada --name "..." --input structured.json --write
5. yarn export-hromadas          # refresh data/releases/hromadas.json
6. yarn match && yarn export-matching-edges
```

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
  "raw_text_path": "scripts/retrieval/raw/nizhyn.txt",
  "notes": ""
}
```

Status values: `pending` | `downloaded` | `structured` | `failed`

## Batch runner

```bash
./scripts/retrieval/run-batch.sh
```

Processes queue entries with `status=downloaded` through
`yarn structure-hromada --write`. Requires NocoDB credentials in `.env`.

## Cost notes

- **Retrieval** (finding URLs, fighting Cloudflare): still mostly manual or
  agent-assisted — CKAN covers ~123 datasets, not full coverage.
- **Structuring** (raw text → JSON): done in-session by the agent; no external
  LLM API. `structure-hromada-strategy.ts` only stores the resulting JSON.

## Target

Pilot batch: +10–20 hromadas from CKAN hits with clear PDF links.
Next milestone: 150 text-mined hromadas for meaningful graph validation.
