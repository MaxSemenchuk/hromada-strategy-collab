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
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");
const PORT = Number(process.env.PORT ?? 5175);
const MAX_TOOL_ITERATIONS = 8;
const SERVER_API_KEY = process.env.OPENAI_API_KEY ?? "";

const SYSTEM_PROMPT = `You are a data analyst assistant for the "hromada-strategy-collab" project \
(candidate МСС / inter-municipal-cooperation agreements between Ukrainian hromadas). \
You have MCP tools over the project's data/releases/*.json, loaded into SQLite:
- get_context: methodology caveats — call this once early in a fresh conversation before \
interpreting scores.
- list_tables / describe_table: schema discovery — call before writing SQL against a table \
you haven't seen yet.
- query: run read-only SQL (SQLite dialect, json_extract/json_each for nested JSON columns).
Answer in the language the user writes in. Ground claims in actual query results — don't \
guess numbers. Keep answers concise; show the key figures, not the whole result set.`;

interface ToolCallTrace {
  name: string;
  input: unknown;
  output: string;
  isError: boolean;
}

interface ChatTurn {
  role: "user" | "assistant";
  text?: string;
  toolCalls?: ToolCallTrace[];
}

let conversation: OpenAI.ChatCompletionMessageParam[] = [
  { role: "system", content: SYSTEM_PROMPT },
];
let transcript: ChatTurn[] = [];

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

async function readJsonBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  const raw = Buffer.concat(chunks).toString("utf-8");
  return raw ? JSON.parse(raw) : {};
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
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
      const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);

      if (req.method === "GET" && url.pathname === "/") {
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
          transcript,
        });
        return;
      }

      if (req.method === "POST" && url.pathname === "/api/reset") {
        conversation = [{ role: "system", content: SYSTEM_PROMPT }];
        transcript = [];
        sendJson(res, 200, { ok: true });
        return;
      }

      if (req.method === "POST" && url.pathname === "/api/chat") {
        const body = await readJsonBody(req);
        const apiKey = String(body.apiKey ?? "") || SERVER_API_KEY;
        const model = String(body.model ?? "gpt-5");
        const message = String(body.message ?? "").trim();

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

        transcript.push({ role: "user", text: message });
        try {
          const { reply, toolCalls } = await runAgentLoop(apiKey, model, message);
          transcript.push({ role: "assistant", text: reply, toolCalls });
          sendJson(res, 200, { reply, toolCalls });
        } catch (err) {
          const msg = describeOpenAiError(err);
          transcript.push({ role: "assistant", text: `⚠ ${msg}` });
          sendJson(res, 502, { error: msg });
        }
        return;
      }

      sendJson(res, 404, { error: "Not found" });
    } catch (err) {
      sendJson(res, 500, { error: (err as Error).message });
    }
  });

  server.listen(PORT, () => {
    console.log(`hromada-data MCP test UI: http://localhost:${PORT}`);
    console.log(`Connected to MCP server — ${tableSummary.count} tables loaded.`);
    console.log(SERVER_API_KEY ? "Using OPENAI_API_KEY from .env by default." : "No .env OPENAI_API_KEY — paste one in the UI.");
  });
}

main().catch((err) => {
  console.error("Failed to start test UI server:", err);
  process.exit(1);
});
