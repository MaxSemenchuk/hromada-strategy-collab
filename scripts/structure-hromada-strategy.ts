/**
 * Write a pre-structured hromada JSON blob into NocoDB (and/or scripts/hromada-output/).
 *
 * Structuring itself is done in-session (agent reads raw strategy text and produces
 * the schema JSON). This script only persists that JSON — no external LLM.
 *
 * Usage:
 *   yarn structure-hromada --name "Ніжинська громада" --json path/to/structured.json
 *   yarn structure-hromada --name "..." --json structured.json --write
 *   yarn structure-hromada --name "..." --json structured.json --write --update 12
 *
 * Schema keys (snake_case in JSON file):
 *   goals, projects, strengths, challenges, partners_mentioned, mss_agreements,
 *   source_quality ("full-strategy"|"partial"|"proxy-info"), confidence_notes,
 *   donors_programs (string[])
 */

import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const NC_URL = process.env.NOCODB_URL || "";
const NC_TOKEN = process.env.NOCODB_TOKEN || "";
const HROMADAS_TABLE_ID = process.env.NOCODB_TABLE_HROMADAS || "mjtetfuixggp5lg";

const FIELDS = ["goals", "projects", "strengths", "challenges", "partners_mentioned", "mss_agreements", "source_quality", "confidence_notes", "donors_programs"] as const;
const DONOR_PROGRAM_OPTIONS = ["EGAP", "DOBRE", "GIZ", "U-LEAD", "DECIDE", "ПРООН/UNDP", "МФ Відродження", "Ре:Форм", "DESPRO"] as const;
const SOURCE_QUALITY = ["full-strategy", "partial", "proxy-info"] as const;

function parseArgs() {
    const args = process.argv.slice(2);
    const get = (flag: string) => {
        const i = args.indexOf(flag);
        return i >= 0 ? args[i + 1] : undefined;
    };
    return {
        name: get("--name"),
        json: get("--json"),
        write: args.includes("--write"),
        updateId: get("--update"),
    };
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
        } else {
            out[f] = typeof raw?.[f] === "string" ? raw[f] : (raw?.[f] ?? "");
        }
    }
    return out;
}

async function writeToNocoDB(name: string, structured: any, updateId?: string) {
    if (!NC_URL || !NC_TOKEN) {
        console.error("Missing NOCODB_URL or NOCODB_TOKEN — cannot write. Set them in .env or omit --write.");
        process.exit(1);
    }
    const body = {
        Name: name,
        Goals: structured.goals,
        Projects: structured.projects,
        Strengths: structured.strengths,
        Challenges: structured.challenges,
        PartnersMentioned: structured.partners_mentioned,
        MSSAgreements: structured.mss_agreements,
        SourceQuality: structured.source_quality,
        ConfidenceNotes: structured.confidence_notes,
        DonorsPrograms: (structured.donors_programs ?? []).join(","),
        ExtractedAt: new Date().toISOString(),
    };
    const endpoint = `${NC_URL}/api/v2/tables/${HROMADAS_TABLE_ID}/records`;
    const method = updateId ? "PATCH" : "POST";
    const payload = updateId ? { Id: Number(updateId), ...body } : body;
    const res = await fetch(endpoint, {
        method,
        headers: { "xc-token": NC_TOKEN, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`NocoDB ${method} ${res.status}: ${text}`);
    }
    const result = await res.json();
    console.log(updateId ? `Updated NocoDB row Id ${updateId}.` : `Created NocoDB row Id ${result.Id ?? result.id}.`);
}

async function main() {
    const { name, json, write, updateId } = parseArgs();
    if (!name || !json) {
        console.error(
            'Usage: yarn structure-hromada --name "<hromada name>" --json <structured.json> [--write] [--update <rowId>]',
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

    if (write) {
        await writeToNocoDB(name, structured, updateId);
    } else {
        console.log("\nNot written to NocoDB (pass --write to insert, --update <rowId> to update an existing row).");
    }
}

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
