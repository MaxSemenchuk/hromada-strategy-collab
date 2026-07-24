/**
 * Export the `Hromadas` table to data/releases/hromadas.json — the canonical,
 * redistributable snapshot of the dataset (CC BY 4.0, see DATA-LICENSE.md).
 *
 * Default: live pull from NocoDB (requires NOCODB_TOKEN + NOCODB_TABLE_HROMADAS
 * in .env). Fallback when no credentials: pass --from-snapshot to normalize a
 * dated research-log NocoDB dump instead.
 *
 * Usage:
 *   yarn export-hromadas
 *   yarn export-hromadas:snapshot
 *   tsx scripts/export-hromadas.ts --from-snapshot data/research-log/hromadas_full54.json
 */

import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

const NC_URL = process.env.NOCODB_URL || "http://localhost:8080";
const NC_TOKEN = process.env.NOCODB_TOKEN || "";
const HROMADAS_TABLE_ID = process.env.NOCODB_TABLE_HROMADAS || "";

function argValue(flag: string): string | undefined {
    const idx = process.argv.indexOf(flag);
    return idx >= 0 ? process.argv[idx + 1] : undefined;
}

const snapshotPath = argValue("--from-snapshot");
const useNocoDb = !snapshotPath && NC_TOKEN && HROMADAS_TABLE_ID;

if (!snapshotPath && !useNocoDb) {
    console.error(
        "Missing NOCODB_TOKEN or NOCODB_TABLE_HROMADAS (.env), and no --from-snapshot given.\n" +
            "  Live export: set credentials in .env, then run yarn export-hromadas\n" +
            "  Offline:     yarn export-hromadas:snapshot"
    );
    process.exit(1);
}

type RawRecord = Record<string, unknown>;

function normalizeRecord(r: RawRecord) {
    const sectors = r.Sectors;
    return {
        Name: r.Name ?? null,
        Katottg: r.Katottg ?? r["Koatuu / Katottg"] ?? r.KATOTTG ?? null,
        Oblast: r.Oblast ?? null,
        Rayon: r.Rayon ?? null,
        Type: r.Type ?? null,
        Population: r.Population ?? null,
        StrategyUrl: r.StrategyUrl ?? null,
        StrategyYear: r.StrategyYear ?? null,
        StrategyPeriod: r.StrategyPeriod ?? null,
        Goals: r.Goals ?? null,
        Sectors: Array.isArray(sectors)
            ? sectors.map((s: unknown) =>
                  typeof s === "string" ? s : (s as { Title?: string })?.Title
              ).filter(Boolean)
            : [],
        Projects: r.Projects ?? null,
        Strengths: r.Strengths ?? null,
        Challenges: r.Challenges ?? null,
        PartnersMentioned: r.PartnersMentioned ?? null,
        MSSAgreements: r.MSSAgreements ?? null,
        // Comma-separated controlled vocab (see structure-hromada-strategy.ts).
        // Absence = "not found in tagging pass," not "no program." Floor coverage.
        DonorsPrograms: (() => {
            const raw = r.DonorsPrograms;
            if (raw == null || raw === "") return [];
            if (Array.isArray(raw)) {
                return raw
                    .map((x) => (typeof x === "string" ? x : (x as { Title?: string })?.Title))
                    .filter(Boolean) as string[];
            }
            return String(raw)
                .split(/[,;]/)
                .map((s) => s.trim())
                .filter(Boolean);
        })(),
        SourceQuality: r.SourceQuality ?? null,
        ExtractedAt: r.ExtractedAt ?? null,
    };
}

function writeRelease(cleaned: ReturnType<typeof normalizeRecord>[], source: string) {
    const textMined = cleaned.filter((r) => r.SourceQuality != null).length;

    const manifest = {
        generatedAt: new Date().toISOString(),
        source,
        totalRows: cleaned.length,
        textMinedRows: textMined,
        schema: "see docs/hromadas-schema.md",
        license: "CC BY 4.0 — see DATA-LICENSE.md",
    };

    const outDir = join(__dirname, "..", "data", "releases");
    writeFileSync(join(outDir, "hromadas.json"), JSON.stringify(cleaned, null, 2));
    writeFileSync(join(outDir, "hromadas.manifest.json"), JSON.stringify(manifest, null, 2));

    console.log(`  Wrote data/releases/hromadas.json (${cleaned.length} rows, ${textMined} text-mined).`);
    console.log("  Wrote data/releases/hromadas.manifest.json.");
}

async function nc(endpoint: string) {
    const res = await fetch(`${NC_URL}${endpoint}`, {
        headers: { "xc-token": NC_TOKEN },
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`NocoDB GET ${endpoint}: ${res.status} ${text}`);
    }
    return res.json();
}

async function fetchAllRecords(tableId: string): Promise<RawRecord[]> {
    const records: RawRecord[] = [];
    let offset = 0;
    const limit = 100;
    while (true) {
        const page = await nc(
            `/api/v2/tables/${tableId}/records?limit=${limit}&offset=${offset}&nested[Sectors][fields]=Title`
        );
        records.push(...(page.list || []));
        if (page.pageInfo?.isLastPage) break;
        offset += limit;
    }
    return records;
}

function loadSnapshot(path: string): RawRecord[] {
    const raw = JSON.parse(readFileSync(path, "utf-8"));
    if (Array.isArray(raw)) return raw;
    if (Array.isArray(raw.list)) return raw.list;
    throw new Error(`Unrecognized snapshot format in ${path} — expected { list: [...] } or [...]`);
}

function normalizeNameKey(name: string): string {
    return name
        .toLowerCase()
        .replace(/\s+(міська|сільська|селищна)\s+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function loadKatottgLookup(): Map<string, string> {
    const mergedPath = join(__dirname, "..", "data", "research-log", "merged_hromadas.json");
    const lookup = new Map<string, string>();
    try {
        const merged = JSON.parse(readFileSync(mergedPath, "utf-8"));
        for (const row of merged.merged || []) {
            if (row.katottg && row.full_name_decen) {
                lookup.set(normalizeNameKey(row.full_name_decen), row.katottg);
            }
        }
    } catch {
        // optional enrichment
    }
    return lookup;
}

function enrichKatottg(cleaned: ReturnType<typeof normalizeRecord>[]) {
    const lookup = loadKatottgLookup();
    for (const row of cleaned) {
        if (row.Katottg || !row.Name) continue;
        const hit = lookup.get(normalizeNameKey(row.Name));
        if (hit) row.Katottg = hit;
    }
}

async function main() {
    let cleaned: ReturnType<typeof normalizeRecord>[];
    let source: string;

    if (snapshotPath) {
        console.log(`Loading snapshot ${snapshotPath}...`);
        const records = loadSnapshot(snapshotPath);
        console.log(`  Loaded ${records.length} rows.`);
        cleaned = records.map(normalizeRecord);
        source = `snapshot:${snapshotPath}`;
    } else {
        console.log("Fetching Hromadas table from NocoDB...");
        const records = await fetchAllRecords(HROMADAS_TABLE_ID);
        console.log(`  Fetched ${records.length} rows.`);
        cleaned = records.map(normalizeRecord);
        source = "nocodb:live";
    }

    enrichKatottg(cleaned);

    writeRelease(cleaned, source);
}

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
