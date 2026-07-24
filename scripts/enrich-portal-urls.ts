/**
 * Offline: add PortalUrl to the current data/releases/hromadas.json and write
 * hromada-portals.json without hitting NocoDB.
 *
 * Usage: yarn enrich-portal-urls
 */

import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { loadPortalOverrides, resolvePortalUrl } from "./lib/portal-url";

const root = join(__dirname, "..");
const releases = join(root, "data", "releases");
const overrides = loadPortalOverrides(root);

type Row = {
    Name?: string | null;
    Katottg?: string | null;
    StrategyUrl?: string | null;
    PortalUrl?: string | null;
    [k: string]: unknown;
};

function main() {
    const path = join(releases, "hromadas.json");
    const rows = JSON.parse(readFileSync(path, "utf-8")) as Row[];
    let withPortal = 0;
    for (const row of rows) {
        row.PortalUrl = resolvePortalUrl({
            strategyUrl: row.StrategyUrl,
            katottg: row.Katottg,
            name: row.Name,
            overrides,
        });
        if (row.PortalUrl) withPortal++;
    }

    // Stable field order: insert PortalUrl right after StrategyUrl when serializing
    const ordered = rows.map((r) => {
        const out: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(r)) {
            if (k === "PortalUrl") continue;
            out[k] = v;
            if (k === "StrategyUrl") out.PortalUrl = r.PortalUrl ?? null;
        }
        if (!("PortalUrl" in out)) out.PortalUrl = r.PortalUrl ?? null;
        return out;
    });

    writeFileSync(path, JSON.stringify(ordered, null, 2) + "\n");

    const portalsIndex = ordered
        .filter((r) => r.PortalUrl)
        .map((r) => ({
            Name: r.Name,
            Katottg: r.Katottg,
            Oblast: r.Oblast,
            Population: r.Population,
            PortalUrl: r.PortalUrl,
            StrategyUrl: r.StrategyUrl,
            SourceQuality: r.SourceQuality,
        }))
        .sort((a, b) => String(a.Name || "").localeCompare(String(b.Name || ""), "uk"));

    writeFileSync(join(releases, "hromada-portals.json"), JSON.stringify(portalsIndex, null, 2) + "\n");

    const manifestPath = join(releases, "hromadas.manifest.json");
    try {
        const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
        manifest.portalUrlRows = withPortal;
        manifest.portalUrlEnrichedAt = new Date().toISOString();
        writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n");
    } catch {
        /* optional */
    }

    console.log(`PortalUrl set on ${withPortal}/${rows.length} rows.`);
    console.log(`Wrote ${portalsIndex.length} entries to data/releases/hromada-portals.json`);
}

main();
