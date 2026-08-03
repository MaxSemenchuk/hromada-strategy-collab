/**
 * Create NocoDB "Hromadas" table for the hromada strategy collaboration pilot.
 *
 * Stores extracted strategy data per territorial community (hromada): goals,
 * sectors (linked to Tags), projects, strengths/challenges, partners, MSS intents.
 *
 * Usage: yarn setup-hromadas
 *
 * Safe to re-run: skips table/columns that already exist.
 */

const NC_URL = process.env.NOCODB_URL || "http://localhost:8080";
const NC_TOKEN = process.env.NOCODB_TOKEN || "";
const BASE_ID = process.env.NOCODB_BASE_ID || "";

if (!NC_TOKEN || !BASE_ID) {
    console.error("Missing NOCODB_TOKEN or NOCODB_BASE_ID. Set them in .env");
    process.exit(1);
}

async function nc(method: string, endpoint: string, body?: any) {
    const res = await fetch(`${NC_URL}${endpoint}`, {
        method,
        headers: { "xc-token": NC_TOKEN, "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`NocoDB ${method} ${endpoint}: ${res.status} ${text}`);
    }
    return res.json();
}

function hasColumn(meta: any, title: string): boolean {
    return (meta.columns || []).some((c: any) => c.title === title);
}

async function addLinkColumn(parentTableId: string, childTableId: string, title: string) {
    console.log(`  Adding "${title}" link column...`);
    await nc("POST", `/api/v2/meta/tables/${parentTableId}/columns`, {
        title,
        uidt: "Links",
        type: "mm",
        parentId: parentTableId,
        childId: childTableId,
    });
    console.log(`  "${title}" link column created.`);
}

async function main() {
    console.log("=== Setting up Hromadas table ===\n");

    const tablesRes = await nc("GET", `/api/v2/meta/bases/${BASE_ID}/tables`, undefined);
    const tableMap: Record<string, { id: string; title: string }> = {};
    for (const t of tablesRes.list || []) {
        tableMap[t.title.toLowerCase()] = { id: t.id, title: t.title };
    }

    const tagsTable = tableMap["tags"];
    if (!tagsTable) {
        throw new Error("Tags table not found. Existing tables: " + Object.keys(tableMap).join(", "));
    }
    console.log(`Found Tags table: ${tagsTable.id}\n`);

    let hromadasTableId: string;
    if (tableMap["hromadas"]) {
        hromadasTableId = tableMap["hromadas"].id;
        console.log(`"Hromadas" already exists (${hromadasTableId}), skipping creation.`);
    } else {
        console.log('Creating "Hromadas" table...');
        const created = await nc("POST", `/api/v2/meta/bases/${BASE_ID}/tables`, {
            table_name: "hromadas",
            title: "Hromadas",
            columns: [
                { column_name: "name", title: "Name", uidt: "SingleLineText" },
                { column_name: "katottg", title: "KATOTTG", uidt: "SingleLineText" },
                { column_name: "oblast", title: "Oblast", uidt: "SingleLineText" },
                { column_name: "rayon", title: "Rayon", uidt: "SingleLineText" },
                { column_name: "type", title: "Type", uidt: "SingleLineText" },
                { column_name: "population", title: "Population", uidt: "Number" },
                { column_name: "strategy_url", title: "StrategyUrl", uidt: "URL" },
                { column_name: "strategy_year", title: "StrategyYear", uidt: "Number" },
                { column_name: "strategy_period", title: "StrategyPeriod", uidt: "SingleLineText" },
                { column_name: "goals", title: "Goals", uidt: "LongText" },
                { column_name: "projects", title: "Projects", uidt: "LongText" },
                { column_name: "strengths", title: "Strengths", uidt: "LongText" },
                { column_name: "challenges", title: "Challenges", uidt: "LongText" },
                { column_name: "partners_mentioned", title: "PartnersMentioned", uidt: "LongText" },
                { column_name: "mss_agreements", title: "MSSAgreements", uidt: "LongText" },
                { column_name: "source_quality", title: "SourceQuality", uidt: "SingleLineText" },
                { column_name: "extracted_at", title: "ExtractedAt", uidt: "DateTime" },
                { column_name: "confidence_notes", title: "ConfidenceNotes", uidt: "LongText" },
            ],
        });
        hromadasTableId = created.id;
        console.log(`  Created with Id: ${hromadasTableId}`);
    }

    const hromadasMeta = await nc("GET", `/api/v2/meta/tables/${hromadasTableId}`, undefined);
    if (!hasColumn(hromadasMeta, "Sectors")) {
        await addLinkColumn(hromadasTableId, tagsTable.id, "Sectors");
    } else {
        console.log('Hromadas: "Sectors" link already exists.');
    }

    console.log("\n=== Done ===");
    console.log(`Hromadas table: ${hromadasTableId}`);
    console.log("\nAdd to .env / memory:");
    console.log(`NOCODB_TABLE_HROMADAS=${hromadasTableId}`);
}

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
