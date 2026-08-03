/**
 * Normalize a research-log / dump snapshot into data/releases/hromadas.json —
 * the canonical, redistributable dataset (CC BY 4.0, see DATA-LICENSE.md).
 *
 * Live NocoDB pull was removed; see scripts/legacy/nocodb/.
 *
 * Usage:
 *   yarn export-hromadas
 *   yarn export-hromadas:snapshot
 *   tsx scripts/export-hromadas.ts --from-snapshot data/research-log/hromadas_full54.json
 */

import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { loadPortalOverrides, resolvePortalUrl } from "./lib/portal-url";

const DEFAULT_SNAPSHOT = "data/research-log/hromadas_full54.json";
const portalOverrides = loadPortalOverrides(join(__dirname, ".."));

function argValue(flag: string): string | undefined {
    const idx = process.argv.indexOf(flag);
    return idx >= 0 ? process.argv[idx + 1] : undefined;
}

const snapshotPath = argValue("--from-snapshot") || DEFAULT_SNAPSHOT;

type RawRecord = Record<string, unknown>;

function normalizeRecord(r: RawRecord) {
    const sectors = r.Sectors;
    const strategyUrl = (r.StrategyUrl as string | null | undefined) ?? null;
    const katottg = (r.Katottg ?? r["Koatuu / Katottg"] ?? r.KATOTTG ?? null) as string | null;
    const name = (r.Name as string | null | undefined) ?? null;
    return {
        Name: name,
        Katottg: katottg,
        Oblast: r.Oblast ?? null,
        Rayon: r.Rayon ?? null,
        Type: r.Type ?? null,
        Population: r.Population ?? null,
        StrategyUrl: strategyUrl,
        PortalUrl: resolvePortalUrl({
            strategyUrl,
            katottg,
            name,
            overrides: portalOverrides,
        }),
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
    const withPortal = cleaned.filter((r) => r.PortalUrl).length;

    const manifest = {
        generatedAt: new Date().toISOString(),
        source,
        totalRows: cleaned.length,
        textMinedRows: textMined,
        portalUrlRows: withPortal,
        schema: "see docs/hromadas-schema.md",
        license: "CC BY 4.0 — see DATA-LICENSE.md",
    };

    const portalsIndex = cleaned
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

    const outDir = join(__dirname, "..", "data", "releases");
    writeFileSync(join(outDir, "hromadas.json"), JSON.stringify(cleaned, null, 2));
    writeFileSync(join(outDir, "hromadas.manifest.json"), JSON.stringify(manifest, null, 2));
    writeFileSync(join(outDir, "hromada-portals.json"), JSON.stringify(portalsIndex, null, 2));

    console.log(`  Wrote data/releases/hromadas.json (${cleaned.length} rows, ${textMined} text-mined, ${withPortal} with PortalUrl).`);
    console.log("  Wrote data/releases/hromadas.manifest.json.");
    console.log(`  Wrote data/releases/hromada-portals.json (${portalsIndex.length} portals).`);
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

/** Recompute PortalUrl after Katottg enrichment so by_katottg overrides apply. */
function enrichPortalUrl(cleaned: ReturnType<typeof normalizeRecord>[]) {
    for (const row of cleaned) {
        row.PortalUrl = resolvePortalUrl({
            strategyUrl: row.StrategyUrl,
            katottg: row.Katottg,
            name: row.Name,
            overrides: portalOverrides,
        });
    }
}

function main() {
    console.log(`Loading snapshot ${snapshotPath}...`);
    const records = loadSnapshot(snapshotPath);
    console.log(`  Loaded ${records.length} rows.`);
    const cleaned = records.map(normalizeRecord);
    enrichKatottg(cleaned);
    enrichPortalUrl(cleaned);
    writeRelease(cleaned, `snapshot:${snapshotPath}`);
}

main();
