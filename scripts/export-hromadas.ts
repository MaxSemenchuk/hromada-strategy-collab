/**
 * Export the live `Hromadas` NocoDB table to data/releases/hromadas.json —
 * the canonical, redistributable snapshot of the dataset (CC BY 4.0, see
 * DATA-LICENSE.md). Re-run this whenever the release should be refreshed;
 * it always overwrites the full file, no incremental merge.
 *
 * Usage: yarn export-hromadas
 */

import { writeFileSync } from "fs";
import { join } from "path";

const NC_URL = process.env.NOCODB_URL || "http://localhost:8080";
const NC_TOKEN = process.env.NOCODB_TOKEN || "";
const HROMADAS_TABLE_ID = process.env.NOCODB_TABLE_HROMADAS || "";

if (!NC_TOKEN || !HROMADAS_TABLE_ID) {
    console.error("Missing NOCODB_TOKEN or NOCODB_TABLE_HROMADAS. Set them in .env");
    process.exit(1);
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

async function fetchAllRecords(tableId: string): Promise<any[]> {
    const records: any[] = [];
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

async function main() {
    console.log("Fetching Hromadas table from NocoDB...");
    const records = await fetchAllRecords(HROMADAS_TABLE_ID);
    console.log(`  Fetched ${records.length} rows.`);

    const cleaned = records.map((r) => ({
        Name: r.Name ?? null,
        Katottg: r.Katottg ?? r["Koatuu / Katottg"] ?? null,
        Oblast: r.Oblast ?? null,
        Rayon: r.Rayon ?? null,
        Type: r.Type ?? null,
        Population: r.Population ?? null,
        StrategyUrl: r.StrategyUrl ?? null,
        StrategyYear: r.StrategyYear ?? null,
        StrategyPeriod: r.StrategyPeriod ?? null,
        Goals: r.Goals ?? null,
        Sectors: (r.Sectors || []).map((s: any) => s.Title).filter(Boolean),
        Projects: r.Projects ?? null,
        Strengths: r.Strengths ?? null,
        Challenges: r.Challenges ?? null,
        PartnersMentioned: r.PartnersMentioned ?? null,
        MSSAgreements: r.MSSAgreements ?? null,
        SourceQuality: r.SourceQuality ?? null,
        ExtractedAt: r.ExtractedAt ?? null,
    }));

    const textMined = cleaned.filter((r) => r.SourceQuality != null).length;

    const manifest = {
        generatedAt: new Date().toISOString(),
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

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
