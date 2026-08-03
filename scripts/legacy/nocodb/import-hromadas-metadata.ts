/**
 * One-off bulk import: fill the Hromadas table with lightweight metadata
 * (KATOTTG code, Population) for all 1,469 mainland Ukrainian hromadas.
 *
 * Sources merged in a prior Python pass (see scratchpad build_hromadas.py /
 * match_existing.py): official KATOTTG classifier (Мінрегіон) + population
 * scraped from decentralization.gov.ua oblast listing pages.
 *
 * Reads two JSON files:
 *   - hromada_updates.json: [{ Id, KATOTTG?, Population? }, ...] — patches for
 *     the 57 hromadas that already have full strategy data.
 *   - hromada_inserts.json: [{ Name, Oblast, Rayon, Type, KATOTTG, Population }, ...]
 *     — new metadata-only rows for the remaining ~1,412 hromadas.
 *
 * Usage: yarn import-hromadas --updates <path> --inserts <path>
 */

import fs from "fs";

const NC_URL = process.env.NOCODB_URL || "http://localhost:8080";
const NC_TOKEN = process.env.NOCODB_TOKEN || "";
const HROMADAS_TABLE_ID = process.env.NOCODB_TABLE_HROMADAS || "mjtetfuixggp5lg";

if (!NC_TOKEN) {
    console.error("Missing NOCODB_TOKEN. Set it in .env");
    process.exit(1);
}

function argValue(flag: string): string | undefined {
    const idx = process.argv.indexOf(flag);
    return idx >= 0 ? process.argv[idx + 1] : undefined;
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

function chunk<T>(arr: T[], size: number): T[][] {
    const out: T[][] = [];
    for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
    return out;
}

async function main() {
    const updatesPath = argValue("--updates");
    const insertsPath = argValue("--inserts");
    if (!updatesPath || !insertsPath) {
        console.error("Usage: yarn import-hromadas --updates <path> --inserts <path>");
        process.exit(1);
    }

    const updates: Array<{ Id: number; KATOTTG?: string; Population?: number }> = JSON.parse(
        fs.readFileSync(updatesPath, "utf-8")
    );
    const inserts: Array<{
        Name: string;
        Oblast: string;
        Rayon: string | null;
        Type: string | null;
        KATOTTG: string | null;
        Population: number | null;
    }> = JSON.parse(fs.readFileSync(insertsPath, "utf-8"));

    console.log(`=== Importing Hromadas metadata ===`);
    console.log(`Updates (existing rows): ${updates.length}`);
    console.log(`Inserts (new metadata-only rows): ${inserts.length}\n`);

    console.log("Patching existing rows...");
    let patched = 0;
    for (const batch of chunk(updates, 100)) {
        await nc("PATCH", `/api/v2/tables/${HROMADAS_TABLE_ID}/records`, batch);
        patched += batch.length;
        console.log(`  patched ${patched}/${updates.length}`);
    }

    console.log("\nInserting new metadata-only rows...");
    let inserted = 0;
    for (const batch of chunk(inserts, 100)) {
        await nc("POST", `/api/v2/tables/${HROMADAS_TABLE_ID}/records`, batch);
        inserted += batch.length;
        console.log(`  inserted ${inserted}/${inserts.length}`);
    }

    console.log("\n=== Done ===");
}

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
