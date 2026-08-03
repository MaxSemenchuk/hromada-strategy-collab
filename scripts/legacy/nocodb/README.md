# Archived NocoDB sync (unused)

This repo’s **canonical store is `data/releases/*.json`**. The shared W3I
NocoDB `Hromadas` table is no longer part of the day-to-day pipeline.

These scripts are kept only as provenance from the 2026-07 spin-out period:

| File | Former yarn command |
|------|---------------------|
| `setup-hromadas-table.ts` | `yarn setup-hromadas` |
| `import-hromadas-metadata.ts` | `yarn import-hromadas` |
| `export-hromadas-from-nocodb.ts` | live `yarn export-hromadas` (NocoDB pull) |

To grow the corpus now:

```bash
yarn structure-hromada --name "…" --json structured.json --write-release
yarn export-hromadas --from-snapshot data/research-log/hromadas_full54.json  # optional re-normalize
```

Do not re-wire these into `package.json` unless you intentionally restore a
remote CRM sync.
