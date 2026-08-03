/**
 * Write a pre-structured hromada JSON blob into local stores.
 *
 * Structuring itself is done in-session (agent reads raw strategy text and produces
 * the schema JSON). This script only persists that JSON — no external LLM.
 *
 * Always writes `scripts/hromada-output/<name>.json`. With `--write-release`
 * upserts strategy fields into `data/releases/hromadas.json` (matched by Name).
 *
 * Usage:
 *   yarn structure-hromada --name "Ніжинська громада" --json path/to/structured.json
 *   yarn structure-hromada --name "..." --json structured.json --write-release
 *
 * Schema keys (snake_case in JSON file):
 *   goals | strategic_goals[] | operational_goals[]  (goals flattened for release)
 *   projects, strengths, challenges, partners_mentioned, mss_agreements,
 *   mss_intents[] (quotes of explicit МСС language),
 *   source_quality ("full-strategy"|"partial"|"proxy-info"), confidence_notes,
 *   donors_programs (string[])
 *
 * Hierarchy fields are kept in the local hromada-output JSON; the release row
 * still stores flat Goals (strategic + operational lines joined by newline).
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const FIELDS = ["goals", "projects", "strengths", "challenges", "partners_mentioned", "mss_agreements", "source_quality", "confidence_notes", "donors_programs"] as const;
const DONOR_PROGRAM_OPTIONS = [
    "EGAP",
    "DOBRE",
    "GIZ",
    "U-LEAD",
    "DECIDE",
    "ПРООН/UNDP",
    "МФ Відродження",
    "Ре:Форм",
    "DESPRO",
    "JICA",
    "ЄІБ",
    "ЄБРР",
    "AFD",
    "STRATEGY LAB",
] as const;
const SOURCE_QUALITY = ["full-strategy", "partial", "proxy-info"] as const;

function parseArgs() {
    const args = process.argv.slice(2);
    const get = (flag: string) => {
        const i = args.indexOf(flag);
        return i >= 0 ? args[i + 1] : undefined;
    };
    if (args.includes("--write") || args.includes("--update")) {
        console.error(
            "NocoDB sync was removed. Use --write-release to update data/releases/hromadas.json.\n" +
                "Archived scripts: scripts/legacy/nocodb/",
        );
        process.exit(1);
    }
    return {
        name: get("--name"),
        json: get("--json"),
        writeRelease: args.includes("--write-release"),
    };
}

function normalizeNameKey(name: string): string {
    return name
        .toLowerCase()
        .replace(/\s+(міська|сільська|селищна)\s+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function upsertRelease(name: string, structured: any) {
    const releasePath = path.join(__dirname, "..", "data", "releases", "hromadas.json");
    const manifestPath = path.join(__dirname, "..", "data", "releases", "hromadas.manifest.json");
    if (!fs.existsSync(releasePath)) {
        console.error(`Missing ${releasePath} — cannot --write-release.`);
        process.exit(1);
    }
    const rows: any[] = JSON.parse(fs.readFileSync(releasePath, "utf-8"));
    if (!Array.isArray(rows)) {
        console.error("data/releases/hromadas.json must be a JSON array.");
        process.exit(1);
    }
    const key = normalizeNameKey(name);
    const idx = rows.findIndex(
        (r) => r?.Name === name || (r?.Name && normalizeNameKey(String(r.Name)) === key),
    );
    if (idx < 0) {
        console.error(
            `No row in hromadas.json matching "${name}". ` +
                "Add metadata (Name/Katottg/Oblast/…) to the release first, then retry --write-release.",
        );
        process.exit(1);
    }
    const prev = rows[idx];
    rows[idx] = {
        ...prev,
        Goals: structured.goals,
        Projects: structured.projects,
        Strengths: structured.strengths,
        Challenges: structured.challenges,
        PartnersMentioned: structured.partners_mentioned,
        MSSAgreements: structured.mss_agreements,
        SourceQuality: structured.source_quality,
        ExtractedAt: new Date().toISOString(),
        DonorsPrograms:
            Array.isArray(structured.donors_programs) && structured.donors_programs.length
                ? structured.donors_programs
                : prev.DonorsPrograms ?? [],
    };
    fs.writeFileSync(releasePath, JSON.stringify(rows, null, 2) + "\n", "utf-8");

    let manifest: Record<string, unknown> = {};
    if (fs.existsSync(manifestPath)) {
        try {
            manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
        } catch {
            manifest = {};
        }
    }
    const textMined = rows.filter((r) => r.SourceQuality != null).length;
    const portalUrlRows = rows.filter((r) => r.PortalUrl).length;
    manifest = {
        ...manifest,
        generatedAt: new Date().toISOString(),
        source: "local:structure-hromada --write-release",
        totalRows: rows.length,
        textMinedRows: textMined,
        portalUrlRows,
        schema: "see docs/hromadas-schema.md",
        license: "CC BY 4.0 — see DATA-LICENSE.md",
        lastUpsert: name,
    };
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf-8");
    console.log(`Upserted strategy fields into data/releases/hromadas.json (row ${idx}: ${rows[idx].Name}).`);
}

function textOfGoal(g: unknown): string {
    if (typeof g === "string") return g.trim();
    if (g && typeof g === "object" && "text" in (g as object)) {
        return String((g as { text: unknown }).text || "").trim();
    }
    return "";
}

function flattenGoals(raw: any): string {
    if (typeof raw?.goals === "string" && raw.goals.trim()) {
        return raw.goals.trim();
    }
    const strategic = Array.isArray(raw?.strategic_goals) ? raw.strategic_goals : [];
    const operational = Array.isArray(raw?.operational_goals) ? raw.operational_goals : [];
    const lines = [...strategic, ...operational].map(textOfGoal).filter((s) => s.length > 0);
    return lines.join("\n");
}

function normalizeStructured(raw: any): any {
    const out: any = {};
    for (const f of FIELDS) {
        if (f === "donors_programs") {
            const arr = Array.isArray(raw?.[f]) ? raw[f] : [];
            out[f] = arr.filter((p: string) => (DONOR_PROGRAM_OPTIONS as readonly string[]).includes(p));
        } else if (f === "source_quality") {
            const v = raw?.[f];
            out[f] = (SOURCE_QUALITY as readonly string[]).includes(v) ? v : "partial";
        } else if (f === "goals") {
            out[f] = flattenGoals(raw);
        } else {
            out[f] = typeof raw?.[f] === "string" ? raw[f] : (raw?.[f] ?? "");
        }
    }
    // Hierarchy sidecar fields (local JSON only)
    if (Array.isArray(raw?.strategic_goals)) {
        out.strategic_goals = raw.strategic_goals;
    }
    if (Array.isArray(raw?.operational_goals)) {
        out.operational_goals = raw.operational_goals;
    }
    if (Array.isArray(raw?.mss_intents)) {
        out.mss_intents = raw.mss_intents;
    }
    return out;
}

function main() {
    const { name, json, writeRelease } = parseArgs();
    if (!name || !json) {
        console.error(
            'Usage: yarn structure-hromada --name "<hromada name>" --json <structured.json> [--write-release]',
        );
        process.exit(1);
    }
    const raw = JSON.parse(fs.readFileSync(json, "utf-8"));
    const structured = normalizeStructured(raw);

    const outDir = path.join(__dirname, "hromada-output");
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, `${name.replace(/[^\p{L}\p{N}]+/gu, "-")}.json`);
    fs.writeFileSync(outPath, JSON.stringify(structured, null, 2), "utf-8");

    console.log(JSON.stringify(structured, null, 2));
    console.log(`\nSaved to ${outPath}`);
    if (structured.strategic_goals || structured.operational_goals) {
        console.log(
            "(Hierarchy present — also run `yarn build-goals-hierarchy` after adding overrides, then `yarn match`.)",
        );
    }

    if (writeRelease) {
        upsertRelease(name, structured);
    } else {
        console.log(
            "\nLocal only (hromada-output). Pass --write-release to upsert data/releases/hromadas.json.",
        );
    }
}

main();
