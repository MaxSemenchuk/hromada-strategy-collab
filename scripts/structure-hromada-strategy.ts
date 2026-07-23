/**
 * Structure raw hromada strategy text into the Hromadas NocoDB schema using a cheap
 * external LLM instead of burning main-session tokens.
 *
 * Retrieval (WebSearch/WebFetch/Cloudflare-evasion) still happens in-session — this
 * script only handles the "raw text -> structured JSON" step. See
 * project_hromada_strategy_collab memory, "Cost lesson" (2026-07-22).
 *
 * Providers:
 *   - groq (default) — genuinely free, no billing/card needed. Free key:
 *     https://console.groq.com/keys. Set GROQ_API_KEY.
 *   - gemini — free tier is region-gated (Gemini API returns quota=0 for some
 *     countries even with a valid key); needs Google Cloud billing enabled to
 *     use reliably. Set GEMINI_API_KEY and pass --provider gemini.
 *
 * Usage:
 *   yarn structure-hromada --name "Ніжинська громада" --input path/to/raw.txt
 *   cat raw.txt | yarn structure-hromada --name "Ніжинська громада"
 *   yarn structure-hromada --name "..." --input raw.txt --write                # also insert into NocoDB
 *   yarn structure-hromada --name "..." --input raw.txt --write --update 12    # update existing row Id 12
 *   yarn structure-hromada --name "..." --input raw.txt --provider gemini      # use Gemini instead of Groq
 *
 * Output: prints structured JSON to stdout (and to scripts/hromada-output/<name>.json).
 * Does NOT write to NocoDB unless --write is passed.
 */

import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.0-flash";

const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";

const NC_URL = process.env.NOCODB_URL || "";
const NC_TOKEN = process.env.NOCODB_TOKEN || "";
const HROMADAS_TABLE_ID = process.env.NOCODB_TABLE_HROMADAS || "mjtetfuixggp5lg";

const FIELDS = ["goals", "projects", "strengths", "challenges", "partners_mentioned", "mss_agreements", "source_quality", "confidence_notes", "donors_programs"] as const;

const DONOR_PROGRAM_OPTIONS = ["EGAP", "DOBRE", "GIZ", "U-LEAD", "DECIDE", "ПРООН/UNDP", "МФ Відродження", "Ре:Форм", "DESPRO"] as const;

const SCHEMA = {
    type: "OBJECT",
    properties: {
        goals: { type: "STRING", description: "Strategic goals/priorities (Цілі), summarized but substantive — this is the field used for cross-hromada matching, so keep the actual thematic language, not generic paraphrase." },
        projects: { type: "STRING", description: "Concrete named projects/initiatives mentioned (Проєкти)." },
        strengths: { type: "STRING", description: "Stated strengths/advantages of the hromada (SWOT or equivalent)." },
        challenges: { type: "STRING", description: "Stated challenges/problems/weaknesses." },
        partners_mentioned: { type: "STRING", description: "Any neighboring hromadas, cities, or organizations explicitly named as partners, collaborators, or agglomeration members — quote or closely paraphrase the source, do not infer." },
        mss_agreements: { type: "STRING", description: "Any explicit mention of МСС (inter-municipal cooperation) agreements, planned or existing, with named parties." },
        source_quality: { type: "STRING", enum: ["full-strategy", "partial", "proxy-info"], description: "full-strategy = complete official strategy document; partial = fragment/summary/excerpt; proxy-info = reconstructed from indirect sources (news, program names), not an actual strategy document." },
        confidence_notes: { type: "STRING", description: "Anything uncertain, missing, contradictory, or that required inference rather than direct extraction. Empty string if none." },
        donors_programs: { type: "ARRAY", items: { type: "STRING", enum: [...DONOR_PROGRAM_OPTIONS] }, description: `Donor/technical-assistance programs explicitly named as having supported this hromada (funding the strategy itself, or named implementing partners). Only include a program if it is EXPLICITLY named in the source text — never infer from generic "EU support" or "USAID" mentions that don't name one of these specific programs. Pick only from: ${DONOR_PROGRAM_OPTIONS.join(", ")}. Empty array if none of these specific programs are named.` },
    },
    required: [...FIELDS],
};

const SCHEMA_DESCRIPTION = FIELDS.map((f) => `- ${f}: ${(SCHEMA.properties as any)[f].description}`).join("\n");

const PROMPT_PREFIX = `You are structuring a Ukrainian territorial-community (hromada) development strategy document into a fixed JSON schema for a research database. Extract ONLY what is actually stated in the source text below — do not invent, infer beyond what's written, or pad with generic boilerplate. If a field has no real content in the source, return an empty string for it. Keep the original Ukrainian wording for goals/projects/partners (this is used for text-similarity matching later, so paraphrasing away specific language destroys signal).\n\nRespond with a single JSON object containing EXACTLY these keys (all strings, except source_quality which must be one of "full-strategy"/"partial"/"proxy-info"):\n${SCHEMA_DESCRIPTION}\n\nSource text follows:\n\n---\n\n`;

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
        provider: get("--provider") || process.env.LLM_PROVIDER || "groq",
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

async function callGemini(rawText: string): Promise<{ data: any; usage: any }> {
    if (!GEMINI_API_KEY) {
        console.error("Missing GEMINI_API_KEY. Get a key at https://aistudio.google.com/apikey and add it to .env");
        process.exit(1);
    }
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            contents: [{ parts: [{ text: PROMPT_PREFIX + rawText }] }],
            generationConfig: {
                responseMimeType: "application/json",
                responseSchema: SCHEMA,
                temperature: 0.1,
            },
        }),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Gemini API ${res.status}: ${text}`);
    }
    const json = await res.json();
    const text = json.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error(`Unexpected Gemini response shape: ${JSON.stringify(json)}`);
    return { data: normalizeStructured(JSON.parse(text)), usage: json.usageMetadata && { promptTokenCount: json.usageMetadata.promptTokenCount, candidatesTokenCount: json.usageMetadata.candidatesTokenCount, totalTokenCount: json.usageMetadata.totalTokenCount } };
}

async function callGroq(rawText: string): Promise<{ data: any; usage: any }> {
    if (!GROQ_API_KEY) {
        console.error("Missing GROQ_API_KEY. Get a free key at https://console.groq.com/keys (no billing/card required) and add it to .env");
        process.exit(1);
    }
    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: { Authorization: `Bearer ${GROQ_API_KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({
            model: GROQ_MODEL,
            messages: [{ role: "user", content: PROMPT_PREFIX + rawText }],
            response_format: { type: "json_object" },
            temperature: 0.1,
        }),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Groq API ${res.status}: ${text}`);
    }
    const json = await res.json();
    const text = json.choices?.[0]?.message?.content;
    if (!text) throw new Error(`Unexpected Groq response shape: ${JSON.stringify(json)}`);
    const usage = json.usage && { promptTokenCount: json.usage.prompt_tokens, candidatesTokenCount: json.usage.completion_tokens, totalTokenCount: json.usage.total_tokens };
    return { data: normalizeStructured(JSON.parse(text)), usage };
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
    const { name, input, write, updateId, provider } = parseArgs();
    if (!name) {
        console.error("Usage: yarn structure-hromada --name \"<hromada name>\" --input <path> [--write] [--update <rowId>] [--provider groq|gemini]");
        process.exit(1);
    }
    if (provider !== "groq" && provider !== "gemini") {
        console.error(`Unknown provider "${provider}". Use "groq" or "gemini".`);
        process.exit(1);
    }
    const rawText = input ? fs.readFileSync(input, "utf-8") : await readStdin();
    if (!rawText.trim()) {
        console.error("No input text provided (empty file/stdin).");
        process.exit(1);
    }

    const modelName = provider === "groq" ? GROQ_MODEL : GEMINI_MODEL;
    console.log(`Structuring "${name}" (${rawText.length} chars of source text) via ${provider}:${modelName}...`);
    const { data: structured, usage } = provider === "groq" ? await callGroq(rawText) : await callGemini(rawText);

    const outDir = path.join(__dirname, "hromada-output");
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, `${name.replace(/[^\p{L}\p{N}]+/gu, "-")}.json`);
    fs.writeFileSync(outPath, JSON.stringify(structured, null, 2), "utf-8");

    console.log(JSON.stringify(structured, null, 2));
    console.log(`\nSaved to ${outPath}`);
    if (usage) {
        console.log(`Tokens: ${usage.promptTokenCount} prompt + ${usage.candidatesTokenCount} output = ${usage.totalTokenCount} total`);
    }

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
