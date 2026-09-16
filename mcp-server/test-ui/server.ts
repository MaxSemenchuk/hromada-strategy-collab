#!/usr/bin/env node
/**
 * Local test harness for mcp-server/: a tiny HTTP server that
 *   1. spawns & connects to our own MCP server (mcp-server/index.ts) over stdio
 *   2. serves a one-page chat UI (index.html)
 *   3. bridges chat messages to the OpenAI API, running the tool-use loop
 *      against the MCP tools (list_tables / describe_table / query / get_context)
 *
 * The OpenAI API key comes from either the browser (per-request, never written
 * to disk) or OPENAI_API_KEY in this project's .env — this is a local dev tool,
 * not a deployed service.
 *
 * Run: tsx mcp-server/test-ui/server.ts  (or `yarn mcp-test-ui`)
 */

import "dotenv/config";
import OpenAI, {
  AuthenticationError,
  PermissionDeniedError,
  NotFoundError,
  RateLimitError,
  APIError,
} from "openai";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { createServer, type IncomingMessage, type ServerResponse } from "http";
import { createReadStream, existsSync, readFileSync, statSync } from "fs";
import { dirname, extname, join, relative, resolve, sep } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");
const PORT = Number(process.env.PORT ?? 5175);
const MAX_TOOL_ITERATIONS = 10;
const SERVER_API_KEY = process.env.OPENAI_API_KEY ?? "";
const DOCS_DIR = join(REPO_ROOT, "docs");

const SYSTEM_PROMPT = `You are the in-site assistant for «Партнери для МСС» \
(hromada-strategy-collab). Product unit = candidate IMC/МСС agreement: pair · theme · one of 5 \
Law 1508-VII forms. Discovery signals are not legal forms.

Route every question:
1. Counts, joins, filters, oblast stats, known pairs → tool \`query\` (SQLite). Call \
list_tables / describe_table if you do not know the schema. Never SELECT * FROM matching_edges \
without a tight WHERE.
2. Who writes about a theme / river / landfill / named object, or a quote → \`search_chunks\` first. \
Cite hromada name + field. Never invent quotes.
3. What the website says, how a page works, stakeholder copy, AIM-CC, Tkachuk framing, methodology \
explained on the site → \`search_chunks\` with field=site_page (HTML) or site_doc (docs/*.md). \
Cite the file path (e.g. docs/matches.html).
4. «З ким · про що · навіщо» packages → search_chunks field=mss_candidate and/or SQL on \
mss_candidates__hypotheses / mss_candidates__registry_known.

Hard rules:
- Matching \`score\` is a hypothesis unless known=true / status=registry_known.
- Do not treat twinning, Interreg, Law 3668, complementary, or basin as МСС forms or as known:true.
- Goals coverage is ~391/1463 hromadas — do not generalise to all Ukraine.
- Combined score is not «strategy match».
Answer in the user's language. Keep answers short (3–8 sentences or a tight list). Show 3–7 citations max.
Call get_context once if methodology is disputed; otherwise this prompt is enough.`;

interface ToolCallTrace {
  name: string;
  input: unknown;
  output: string;
  isError: boolean;
}

interface Session {
  conversation: OpenAI.ChatCompletionMessageParam[];
  lastUsed: number;
}

const sessions = new Map<string, Session>();
const SESSION_TTL_MS = 60 * 60 * 1000;

const mcpClient = new Client({ name: "hromada-data-test-ui", version: "0.1.0" });
let openaiTools: OpenAI.ChatCompletionTool[] = [];
let tableSummary: { count: number; names: string[] } = { count: 0, names: [] };

async function connectMcp(): Promise<void> {
  const transport = new StdioClientTransport({
    command: "npx",
    args: ["tsx", "mcp-server/index.ts"],
    cwd: REPO_ROOT,
  });
  await mcpClient.connect(transport);

  const { tools } = await mcpClient.listTools();
  openaiTools = tools.map((t) => {
    const { $schema, ...parameters } = (t.inputSchema ?? {
      type: "object",
      properties: {},
    }) as Record<string, unknown>;
    return {
      type: "function",
      function: {
        name: t.name,
        description: t.description ?? "",
        parameters,
      },
    };
  });

  const listTablesResult = await mcpClient.callTool({ name: "list_tables", arguments: {} });
  const firstBlock = (listTablesResult.content as { type: string; text?: string }[])[0];
  if (firstBlock?.type === "text" && firstBlock.text) {
    const rows = JSON.parse(firstBlock.text) as { table: string }[];
    tableSummary = { count: rows.length, names: rows.map((r) => r.table) };
  }
}

function toolResultText(content: unknown): string {
  if (!Array.isArray(content)) return String(content);
  return content
    .map((c) => (c && typeof c === "object" && "text" in c ? String((c as { text: unknown }).text) : JSON.stringify(c)))
    .join("\n");
}

async function runAgentLoop(
  apiKey: string,
  model: string,
  conversation: OpenAI.ChatCompletionMessageParam[],
  userMessage: string,
): Promise<{ reply: string; toolCalls: ToolCallTrace[] }> {
  const client = new OpenAI({ apiKey });
  conversation.push({ role: "user", content: userMessage });

  const toolCalls: ToolCallTrace[] = [];

  for (let i = 0; i < MAX_TOOL_ITERATIONS; i++) {
    const response = await client.chat.completions.create({
      model,
      messages: conversation,
      tools: openaiTools,
      tool_choice: "auto",
    });

    const choice = response.choices[0];
    const message = choice.message;
    conversation.push(message);

    const toolCallsRequested = (message.tool_calls ?? []).filter(
      (tc): tc is OpenAI.ChatCompletionMessageFunctionToolCall => tc.type === "function",
    );

    if (toolCallsRequested.length === 0) {
      if (choice.finish_reason === "length") {
        return { reply: (message.content ?? "") + "\n\n(truncated — hit max_tokens)", toolCalls };
      }
      if (choice.finish_reason === "content_filter") {
        return { reply: "(response withheld by content filter)", toolCalls };
      }
      return { reply: message.content ?? "(no text in response)", toolCalls };
    }

    for (const tc of toolCallsRequested) {
      let outputText: string;
      let isError = false;
      let parsedArgs: unknown = {};
      try {
        parsedArgs = tc.function.arguments ? JSON.parse(tc.function.arguments) : {};
      } catch {
        parsedArgs = tc.function.arguments;
      }
      try {
        const result = await mcpClient.callTool({
          name: tc.function.name,
          arguments: parsedArgs as Record<string, unknown>,
        });
        isError = Boolean(result.isError);
        outputText = toolResultText(result.content);
      } catch (err) {
        isError = true;
        outputText = `Tool execution error: ${(err as Error).message}`;
      }
      if (outputText.length > 12000) outputText = outputText.slice(0, 12000) + "\n…(truncated)";
      toolCalls.push({ name: tc.function.name, input: parsedArgs, output: outputText, isError });
      conversation.push({
        role: "tool",
        tool_call_id: tc.id,
        content: outputText,
      });
    }
  }

  return {
    reply: `(stopped after ${MAX_TOOL_ITERATIONS} tool round-trips without a final answer)`,
    toolCalls,
  };
}

function pruneSessions(): void {
  const now = Date.now();
  for (const [id, s] of sessions) {
    if (now - s.lastUsed > SESSION_TTL_MS) sessions.delete(id);
  }
  if (sessions.size <= 40) return;
  const oldest = [...sessions.entries()].sort((a, b) => a[1].lastUsed - b[1].lastUsed);
  for (const [id] of oldest.slice(0, sessions.size - 40)) sessions.delete(id);
}

function getSession(id: string): Session {
  pruneSessions();
  let s = sessions.get(id);
  if (!s) {
    s = {
      conversation: [{ role: "system", content: SYSTEM_PROMPT }],
      lastUsed: Date.now(),
    };
    sessions.set(id, s);
  }
  s.lastUsed = Date.now();
  return s;
}

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon",
  ".md": "text/markdown; charset=utf-8",
  ".woff2": "font/woff2",
};

function setCors(res: ServerResponse): void {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function serveDocs(urlPath: string, res: ServerResponse): boolean {
  let rel = decodeURIComponent(urlPath.split("?")[0]);
  if (rel === "/") rel = "/index.html";
  if (rel.endsWith("/")) rel += "index.html";
  const abs = resolve(DOCS_DIR, `.${rel}`);
  const inside = relative(DOCS_DIR, abs);
  if (inside.startsWith("..") || inside.split(sep).includes("..")) return false;
  if (!existsSync(abs)) return false;
  const st = statSync(abs);
  if (st.isDirectory()) return false;
  const mime = MIME[extname(abs).toLowerCase()] || "application/octet-stream";
  res.writeHead(200, { "Content-Type": mime, "Cache-Control": "no-cache" });
  createReadStream(abs).pipe(res);
  return true;
}

async function readJsonBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  const raw = Buffer.concat(chunks).toString("utf-8");
  return raw ? JSON.parse(raw) : {};
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  setCors(res);
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(payload);
}

function describeOpenAiError(err: unknown): string {
  if (err instanceof AuthenticationError) return "Invalid OpenAI API key.";
  if (err instanceof PermissionDeniedError) return "API key lacks permission for this model.";
  if (err instanceof NotFoundError) return "Model not found: check the model id.";
  if (err instanceof RateLimitError) return "Rate limited — wait a moment and retry.";
  if (err instanceof APIError) return `OpenAI API error: ${err.message}`;
  return err instanceof Error ? err.message : String(err);
}

async function main(): Promise<void> {
  await connectMcp();

  const server = createServer(async (req, res) => {
    try {
      setCors(res);
      if (req.method === "OPTIONS") {
        res.writeHead(204);
        res.end();
        return;
      }

      const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);

      if (req.method === "GET" && (url.pathname === "/lab" || url.pathname === "/lab/")) {
        const html = readFileSync(join(__dirname, "index.html"), "utf-8");
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end(html);
        return;
      }

      if (req.method === "GET" && url.pathname === "/api/status") {
        sendJson(res, 200, {
          mcpServer: "hromada-data",
          connected: true,
          hasServerKey: Boolean(SERVER_API_KEY),
          tools: openaiTools.map((t) => ({ name: t.function.name, description: t.function.description })),
          tables: tableSummary,
        });
        return;
      }

      if (req.method === "POST" && url.pathname === "/api/reset") {
        const body = await readJsonBody(req);
        const sid = String(body.sessionId ?? "lab");
        sessions.set(sid, {
          conversation: [{ role: "system", content: SYSTEM_PROMPT }],
          lastUsed: Date.now(),
        });
        sendJson(res, 200, { ok: true });
        return;
      }

      if (req.method === "POST" && url.pathname === "/api/chat") {
        const body = await readJsonBody(req);
        const apiKey = String(body.apiKey ?? "") || SERVER_API_KEY;
        const model = String(body.model ?? "gpt-4o-mini");
        const message = String(body.message ?? "").trim();
        const sid = String(body.sessionId ?? "lab");
        const page = String(body.page ?? "");
        const lang = String(body.lang ?? "");

        if (!apiKey) {
          sendJson(res, 400, {
            error: "Missing OpenAI API key (paste one, or set OPENAI_API_KEY in .env).",
          });
          return;
        }
        if (!message) {
          sendJson(res, 400, { error: "Empty message." });
          return;
        }

        const session = getSession(sid);
        const framed =
          page || lang
            ? `[page: ${page || "?"}; lang: ${lang || "?"}; site files are search_chunks field=site_page/site_doc]\n${message}`
            : message;
        try {
          const { reply, toolCalls } = await runAgentLoop(apiKey, model, session.conversation, framed);
          sendJson(res, 200, { reply, toolCalls });
        } catch (err) {
          const msg = describeOpenAiError(err);
          sendJson(res, 502, { error: msg });
        }
        return;
      }

      if (req.method === "GET" && serveDocs(url.pathname, res)) return;

      sendJson(res, 404, { error: "Not found" });
    } catch (err) {
      sendJson(res, 500, { error: (err as Error).message });
    }
  });

  server.listen(PORT, () => {
    console.log(`Site + chat: http://localhost:${PORT}/`);
    console.log(`MCP lab UI:  http://localhost:${PORT}/lab`);
    console.log(`Connected to MCP server — ${tableSummary.count} tables loaded.`);
    console.log(SERVER_API_KEY ? "Using OPENAI_API_KEY from .env by default." : "No .env OPENAI_API_KEY — paste one in the widget settings.");
  });
}

main().catch((err) => {
  console.error("Failed to start test UI server:", err);
  process.exit(1);
});
