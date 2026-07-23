/**
 * Store an agent-produced structured hromada strategy record into the Hromadas
 * NocoDB table.
 *
 * Structuring (raw strategy text -> structured JSON) is done in-session by the
 * agent. This project no longer calls any external LLM — the Groq and Gemini
 * providers were removed. This script only normalizes an already-structured JSON
 * object and (optionally) writes it to NocoDB.
 * See docs/project-history.md ("Cost lesson", 2026-07-22).
 *
 * The input is a JSON object with these keys (strings unless noted):
 *   goals, projects, strengths, challenges, partners_mentioned, mss_agreements,
 *   source_quality ("full-strategy" | "partial" | "proxy-info"),
 *   confidence_notes, donors_programs (array of known program names).
 *
 * Usage:
 *   yarn structure-hromada --name "Ніжинська громада" --input path/to/structured.json
 *   cat structured.json | yarn structure-hromada --name "Ніжинська громада"
 *   yarn structure-hromada --name "..." --input structured.json --write             # also insert into NocoDB
 *   yarn structure-hromada --name "..." --input structured.json --write --update 12  # update existing row Id 12
 *
 * Output: prints the normalized JSON to stdout (and to scripts/hromada-output/<name>.json).
 * Does NOT write to NocoDB unless --write is passed.
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

function parseArgs() {
    const args = process.argv.slice(2);
    const get = (flag: string) => {
        const i = args.indexOf(flag);
        return i >= 0 ? args[i + 1] : undefined;
    };
    return {
        name: get("--name"),
        input: get("--input"),
        write: args.includes("--write"),
        updateId: get("--update"),
    };
}

async function readStdin(): Promise<string> {
    const chunks: Buffer[] = [];
    for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
    return Buffer.concat(chunks).toString("utf-8");
}

function normalizeStructured(raw: any): any {
    const out: any = {};
    for (const f of FIELDS) {
        if (f === "donors_programs") {
            const arr = Array.isArray(raw?.[f]) ? raw[f] : [];
            out[f] = arr.filter((p: string) => (DONOR_PROGRAM_OPTIONS as readonly string[]).includes(p));
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
    const endpoint = updateId
        ? `${NC_URL}/api/v2/tables/${HROMADAS_TABLE_ID}/records`
        : `${NC_URL}/api/v2/tables/${HROMADAS_TABLE_ID}/records`;
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
    const { name, input, write, updateId } = parseArgs();
    if (!name) {
        console.error("Usage: yarn structure-hromada --name \"<hromada name>\" --input <structured.json> [--write] [--update <rowId>]");
        process.exit(1);
    }
    const rawInput = input ? fs.readFileSync(input, "utf-8") : await readStdin();
    if (!rawInput.trim()) {
        console.error("No input provided (empty file/stdin). Expected an agent-produced structured JSON object.");
        process.exit(1);
    }

    let parsed: any;
    try {
        parsed = JSON.parse(rawInput);
    } catch {
        console.error("Input is not valid JSON. This script expects an agent-produced structured JSON object (not raw strategy text).");
        process.exit(1);
    }

    const structured = normalizeStructured(parsed);

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
