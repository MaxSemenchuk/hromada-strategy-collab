#!/usr/bin/env node
/**
 * MCP server exposing data/releases/*.json (the canonical hromada-strategy-collab
 * dataset) as a queryable in-memory SQLite database — "ask anything about our data".
 *
 * Tools:
 *   - get_context     methodology caveats to read before interpreting results
 *   - list_tables     tables + row counts + source files
 *   - describe_table  columns + sample rows + the source file's _meta
 *   - query           run read-only SQL against the loaded tables
 *   - search_chunks   FTS over strategy / DREAM / candidate / twinning text
 *
 * Run directly: tsx mcp-server/index.ts (stdio transport)
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { z } from "zod";
import { loadReleasesIntoDb, type TableInfo } from "./db.js";
import { installTextChunks, searchTextChunks } from "./chunks.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..");

const { db, tables } = loadReleasesIntoDb(REPO_ROOT);
const chunkStats = installTextChunks(db, REPO_ROOT);
tables.push({
  name: "text_chunks",
  sourceFile: "derived: FTS over release text fields (not a public JSON file)",
  rowCount: chunkStats.total,
  columns: [
    { name: "id", type: "TEXT" },
    { name: "name", type: "TEXT" },
    { name: "short", type: "TEXT" },
    { name: "katottg", type: "TEXT" },
    { name: "oblast", type: "TEXT" },
    { name: "field", type: "TEXT" },
    { name: "theme", type: "TEXT" },
    { name: "source", type: "TEXT" },
    { name: "text", type: "TEXT" },
  ],
});
const tablesByName = new Map<string, TableInfo>(tables.map((t) => [t.name, t]));
console.error(
  `hromada-data: ${tables.length} tables, ${chunkStats.total} text chunks ` +
    `(${Object.entries(chunkStats.byField)
      .sort((a, b) => b[1] - a[1])
      .map(([k, n]) => `${k}:${n}`)
      .join(", ")})`,
);

const DEFAULT_ROW_LIMIT = 200;
const MAX_ROW_LIMIT = 2000;

function jsonResult(value: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }] };
}

function errorResult(message: string) {
  return { content: [{ type: "text" as const, text: message }], isError: true as const };
}

const FORBIDDEN_SQL = /\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b/i;

function assertReadOnlySelect(sql: string): string | null {
  const trimmed = sql.trim().replace(/;\s*$/, "");
  if (!/^(select|with)\b/i.test(trimmed)) {
    return "Only SELECT (or WITH ... SELECT) statements are allowed.";
  }
  if (trimmed.includes(";")) {
    return "Only a single statement is allowed (no semicolon-separated statements).";
  }
  if (FORBIDDEN_SQL.test(trimmed)) {
    return "Statement contains a forbidden keyword (writes/schema changes/PRAGMA are not allowed).";
  }
  return null;
}

const server = new McpServer({ name: "hromada-data", version: "0.1.0" });

server.registerTool(
  "get_context",
  {
    title: "Get dataset context & methodology caveats",
    description:
      "Returns the dataset's own README (data/releases/MANIFEST.md) and the project's hard " +
      "methodology rules (.cursor/rules/hromada-project.mdc), e.g. that matching `score` is a " +
      "hypothesis unless `known: true`, that `track` (thematic/operational/mixed) changes how a " +
      "pair should be read, and that sector-tag overlap is NOT a matching signal. Call this BEFORE " +
      "interpreting query results — the raw numbers are easy to misread without it.",
    inputSchema: {},
  },
  async () => {
    const parts: string[] = [];
    try {
      parts.push(
        "# data/releases/MANIFEST.md\n\n" +
          readFileSync(join(REPO_ROOT, "data/releases/MANIFEST.md"), "utf-8"),
      );
    } catch {
      /* ignore missing file */
    }
    try {
      parts.push(
        "# .cursor/rules/hromada-project.mdc\n\n" +
          readFileSync(join(REPO_ROOT, ".cursor/rules/hromada-project.mdc"), "utf-8"),
      );
    } catch {
      /* ignore missing file */
    }
    try {
      parts.push(
        "# docs/README.md (stakeholder site map)\n\n" +
          readFileSync(join(REPO_ROOT, "docs/README.md"), "utf-8"),
      );
    } catch {
      /* ignore missing file */
    }
    return { content: [{ type: "text" as const, text: parts.join("\n\n---\n\n") }] };
  },
);

server.registerTool(
  "list_tables",
  {
    title: "List queryable tables",
    description:
      "Lists every table loaded from data/releases/*.json: name, row count, source file, and " +
      "columns. Root-array files (e.g. hromadas.json) become one table named after the file; " +
      "root-object files contribute one table per top-level array field, named " +
      "`<file>__<field>` (e.g. `mss_candidates__hypotheses`). A `_meta` table holds each source " +
      "file's non-tabular scalar fields (generatedAt, method, warning, coverage, counts, …), " +
      "keyed by source_file.",
    inputSchema: {},
  },
  async () => {
    return jsonResult(
      tables.map((t) => ({
        table: t.name,
        row_count: t.rowCount,
        source_file: t.sourceFile,
        source_key: t.sourceKey ?? null,
        columns: t.columns.map((c) => c.name),
      })),
    );
  },
);

server.registerTool(
  "describe_table",
  {
    title: "Describe one table",
    description:
      "Column names/types, row count, source file, up to 3 sample rows, and (if present) the " +
      "_meta scalar fields for that table's source file. Object/array-valued JSON fields are " +
      "stored as TEXT — query them with SQLite json_extract()/json_each().",
    inputSchema: { table: z.string().describe("Exact table name from list_tables") },
  },
  async ({ table }) => {
    const info = tablesByName.get(table);
    if (!info) {
      return errorResult(`Unknown table "${table}". Call list_tables to see available names.`);
    }
    const sampleRows = db.prepare(`SELECT * FROM "${table}" LIMIT 3`).all();
    let meta: unknown = null;
    const metaRow = db
      .prepare(`SELECT meta_json FROM _meta WHERE source_file = ?`)
      .get(info.sourceFile) as { meta_json: string } | undefined;
    if (metaRow) meta = JSON.parse(metaRow.meta_json);

    return jsonResult({
      table: info.name,
      source_file: info.sourceFile,
      source_key: info.sourceKey ?? null,
      row_count: info.rowCount,
      columns: info.columns,
      sample_rows: sampleRows,
      source_file_meta: meta,
    });
  },
);

server.registerTool(
  "query",
  {
    title: "Run a read-only SQL query",
    description:
      "Runs a single read-only SELECT (or WITH ... SELECT) against the loaded tables (SQLite " +
      "dialect, JSON1 available: json_extract, json_each, etc.). Call list_tables/describe_table " +
      "first to see what's available, and get_context to avoid misreading scores/tracks. Results " +
      `are truncated to \`limit\` rows (default ${DEFAULT_ROW_LIMIT}, max ${MAX_ROW_LIMIT}); the ` +
      "response also reports the true total row count so you know if it was truncated. " +
      "Prefer search_chunks for 'who writes about X' / quotes; use SQL for counts, joins, and filters. " +
      "Never SELECT * FROM matching_edges without a tight WHERE — it has tens of thousands of rows.",
    inputSchema: {
      sql: z.string().describe("A single SELECT/WITH statement"),
      limit: z
        .number()
        .int()
        .positive()
        .max(MAX_ROW_LIMIT)
        .optional()
        .describe(`Max rows to return (default ${DEFAULT_ROW_LIMIT}, max ${MAX_ROW_LIMIT})`),
    },
  },
  async ({ sql, limit }) => {
    const rejection = assertReadOnlySelect(sql);
    if (rejection) return errorResult(rejection);

    const effectiveLimit = Math.min(limit ?? DEFAULT_ROW_LIMIT, MAX_ROW_LIMIT);
    try {
      const rows = db.prepare(sql).all();
      const truncated = rows.length > effectiveLimit;
      return jsonResult({
        row_count: rows.length,
        truncated,
        rows: truncated ? rows.slice(0, effectiveLimit) : rows,
      });
    } catch (err) {
      return errorResult(`SQL error: ${(err as Error).message}`);
    }
  },
);

const CHUNK_FIELDS = [
  "goals_strategic",
  "goals_operational",
  "goals",
  "strengths",
  "challenges",
  "projects",
  "partners",
  "mss_agreement",
  "mss_intent",
  "donors",
  "dream_title",
  "mss_candidate",
  "twinning",
  "intl_agreement",
  "interreg",
  "site_page",
  "site_doc",
].join(", ");

server.registerTool(
  "search_chunks",
  {
    title: "Search strategy and partnership text",
    description:
      "Full-text search over structured strategy fields AND the stakeholder site (docs/*.html + docs/*.md). " +
      "Use this when the user asks who writes about a theme, river, landfill, named object, wants quotes, " +
      "or asks what the website/pages say (methodology copy, AIM-CC, Tkachuk framing, how a screen works). " +
      `Fields: ${CHUNK_FIELDS}. ` +
      "site_page = public HTML; site_doc = markdown research pages under docs/. Cite path (e.g. docs/matches.html). " +
      "Hits are retrieval evidence — not IMC legal forms, not v7 score, never known:true. " +
      "Coverage is ~391/1463 hromadas with Goals; do not generalise to all Ukraine. " +
      "Law 3668 / twinning / Interreg chunks are international layers, not Law 1508 МСС.",
    inputSchema: {
      query: z.string().describe("Natural-language or keyword query (Ukrainian or English)"),
      field: z
        .string()
        .optional()
        .describe(`Optional field filter; comma-separated from: ${CHUNK_FIELDS}`),
      oblast: z.string().optional().describe("Optional oblast substring, e.g. Чернігівська"),
      katottg: z.string().optional().describe("Optional exact KATOTTG code"),
      limit: z.number().int().positive().max(30).optional().describe("Max hits (default 12, max 30)"),
    },
  },
  async ({ query, field, oblast, katottg, limit }) => {
    const q = query.trim();
    if (!q) return errorResult("Empty query.");
    const { query_used, hits } = searchTextChunks(db, { query: q, field, oblast, katottg, limit });
    return jsonResult({
      corpus_chunks: chunkStats.total,
      query_used,
      hit_count: hits.length,
      hits,
    });
  },
);

const transport = new StdioServerTransport();
server.connect(transport).catch((err) => {
  console.error("Failed to start MCP server:", err);
  process.exit(1);
});
