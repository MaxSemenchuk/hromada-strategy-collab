/**
 * Phase-1 text corpus for chat: structured release fields as FTS5 chunks.
 * Not a matching signal — never fold hits into v7 score / known:true.
 *
 * Indexed: Goals hierarchy, SWOT/projects, explicit-ask quotes, DREAM titles,
 * IMC candidate packages, twinning, Law 3668 titles, Interreg project names,
 * stakeholder site HTML + docs/*.md (scripts/JSON blobs stripped).
 * Not indexed: matching-edges matrix, GISRR general_part, raw PDFs.
 */

import Database from "better-sqlite3";
import { existsSync, readdirSync, readFileSync } from "fs";
import { join } from "path";

export interface TextChunk {
  id: string;
  name: string;
  short: string;
  katottg: string;
  oblast: string;
  field: string;
  theme: string;
  source: string;
  text: string;
}

export interface ChunkStats {
  total: number;
  byField: Record<string, number>;
}

export interface ChunkHit {
  name: string;
  short: string;
  katottg: string;
  oblast: string;
  field: string;
  theme: string;
  source: string;
  text: string;
  rank: number | null;
}

const MIN_LEN = 20;
const MAX_LEN = 1400;

const STOP = new Set([
  "хто", "що", "як", "які", "який", "яка", "яке", "для", "про", "при", "або",
  "та", "і", "й", "в", "у", "на", "з", "зі", "із", "по", "це", "чи", "же",
  "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "who",
  "what", "which", "where", "how", "about", "from",
]);

const SYNONYMS: { test: RegExp; extra: string[] }[] = [
  { test: /вод[ауиіо]|річк|басейн|каналіз|водопостач|sewage|water/i, extra: ["вода", "річка", "басейн", "водопостачання", "каналізація"] },
  { test: /тпв|смітт|полігон|відход|waste|landfill/i, extra: ["ТПВ", "відходи", "сміття", "полігон"] },
  { test: /туризм|спадщин|побратим|tourism|heritage/i, extra: ["туризм", "спадщина"] },
  { test: /цнап|е-уряд|цифров|cnap|digital/i, extra: ["ЦНАП", "цифровізація", "е-урядування"] },
  { test: /мсс|міжмуніцип|співроб|коопер/i, extra: ["МСС", "міжмуніципальне"] },
];

function readJson(path: string): unknown {
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, "utf-8"));
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

function str(v: unknown): string {
  return typeof v === "string" ? v : v == null ? "" : String(v);
}

function shortName(name: string, explicit?: string): string {
  if (explicit) return explicit;
  return name
    .replace(/\s+територіальна громада$/i, "")
    .replace(/\s+(міська|селищна|сільська)$/i, "")
    .trim();
}

function clip(text: string): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= MAX_LEN) return t;
  return t.slice(0, MAX_LEN - 1) + "…";
}

function cleanBullet(s: string): string {
  return (s ?? "").replace(/^[-•*–—]\s+/, "").replace(/^\d+([.)]\d+){0,3}[.)]?\s+/, "").trim();
}

function longEnough(s: string): boolean {
  return s.replace(/\s+/g, " ").trim().length >= MIN_LEN;
}

function splitItems(raw: string): string[] {
  const trimmed = raw.trim();
  if (!trimmed) return [];
  if (trimmed.includes("\n")) {
    return trimmed.split(/\n+/).map(cleanBullet).filter(longEnough);
  }
  const numbered = trimmed.split(/(?=\d+\.\d+(\.\d+)?\.?\s)/).map(cleanBullet).filter(longEnough);
  if (numbered.length > 1) return numbered;
  return longEnough(trimmed) ? [trimmed] : [];
}

type Adder = (partial: Omit<TextChunk, "id">) => void;

function makeAdder(chunks: TextChunk[]): Adder {
  const counters = new Map<string, number>();
  return (partial) => {
    const text = clip(partial.text);
    if (!longEnough(text)) return;
    const key = `${partial.katottg || partial.name}:${partial.field}`;
    const n = counters.get(key) ?? 0;
    counters.set(key, n + 1);
    const id = `${key}:${n}`;
    chunks.push({ ...partial, id, text });
  };
}

function addHromadas(add: Adder, repoRoot: string, skipGoals: Set<string>): void {
  const raw = readJson(join(repoRoot, "data/releases/hromadas.json"));
  const rows = Array.isArray(raw) ? raw : [];
  for (const item of rows) {
    const row = asRecord(item);
    if (!row) continue;
    const name = str(row.Name);
    const kat = str(row.Katottg);
    const oblast = str(row.Oblast);
    const short = shortName(name);
    const base = { name, short, katottg: kat, oblast, theme: "", source: "hromadas.json" };
    if (!skipGoals.has(kat)) {
      for (const line of splitItems(str(row.Goals))) {
        add({ ...base, field: "goals", text: line });
      }
    }
    for (const line of splitItems(str(row.Strengths))) add({ ...base, field: "strengths", text: line });
    for (const line of splitItems(str(row.Challenges))) add({ ...base, field: "challenges", text: line });
    for (const line of splitItems(str(row.Projects))) add({ ...base, field: "projects", text: line });
    for (const line of splitItems(str(row.PartnersMentioned))) add({ ...base, field: "partners", text: line });
    for (const line of splitItems(str(row.MSSAgreements))) add({ ...base, field: "mss_agreement", text: line });
    const donors = row.DonorsPrograms;
    if (Array.isArray(donors) && donors.length > 0) {
      add({ ...base, field: "donors", text: `Донорські програми: ${donors.map(str).filter(Boolean).join(", ")}` });
    }
  }
}

function addHierarchy(add: Adder, repoRoot: string): Set<string> {
  const skip = new Set<string>();
  const raw = asRecord(readJson(join(repoRoot, "data/releases/goals-hierarchy.json")));
  const list = Array.isArray(raw?.hromadas) ? raw.hromadas : [];
  for (const item of list) {
    const row = asRecord(item);
    if (!row) continue;
    const name = str(row.name);
    const kat = str(row.katottg);
    const oblast = str(row.oblast);
    const short = shortName(name);
    if (kat) skip.add(kat);
    const base = { name, short, katottg: kat, oblast, theme: "", source: "goals-hierarchy.json" };
    const strat = Array.isArray(row.strategic_goals) ? row.strategic_goals : [];
    for (const g of strat) {
      const rec = asRecord(g);
      const text = str(rec?.text);
      if (text) add({ ...base, field: "goals_strategic", text });
    }
    const ops = Array.isArray(row.operational_goals) ? row.operational_goals : [];
    for (const g of ops) {
      const rec = asRecord(g);
      const text = str(rec?.text);
      if (text) add({ ...base, field: "goals_operational", text });
    }
  }
  return skip;
}

function addIntents(add: Adder, repoRoot: string): void {
  const raw = asRecord(readJson(join(repoRoot, "data/releases/mss-intents.json")));
  const list = Array.isArray(raw?.hromadas) ? raw.hromadas : [];
  for (const item of list) {
    const row = asRecord(item);
    if (!row) continue;
    const name = str(row.name);
    const kat = str(row.katottg);
    const oblast = str(row.oblast);
    const short = str(row.short) || shortName(name);
    const intents = Array.isArray(row.intents) ? row.intents : [];
    for (const it of intents) {
      const rec = asRecord(it);
      if (!rec) continue;
      const quote = str(rec.quote);
      if (!quote) continue;
      add({
        name,
        short,
        katottg: kat,
        oblast,
        field: "mss_intent",
        theme: str(rec.theme),
        source: "mss-intents.json",
        text: quote,
      });
    }
  }
}

function addDream(add: Adder, repoRoot: string): void {
  const raw = asRecord(readJson(join(repoRoot, "data/releases/dream-priorities.json")));
  const list = Array.isArray(raw?.hromadas) ? raw.hromadas : [];
  for (const item of list) {
    const row = asRecord(item);
    if (!row) continue;
    const name = str(row.name);
    const kat = str(row.katottg);
    const titles = Array.isArray(row.sample_titles) ? row.sample_titles : [];
    for (const t of titles) {
      const title = str(t);
      if (!title) continue;
      add({
        name,
        short: shortName(name),
        katottg: kat,
        oblast: "",
        field: "dream_title",
        theme: "",
        source: "dream-priorities.json",
        text: `DREAM проєкт: ${title}`,
      });
    }
  }
}

function addCandidates(add: Adder, repoRoot: string): void {
  const raw = asRecord(readJson(join(repoRoot, "data/releases/mss-candidates.json")));
  if (!raw) return;
  const groups = [
    ...(Array.isArray(raw.registry_known) ? raw.registry_known : []),
    ...(Array.isArray(raw.hypotheses) ? raw.hypotheses : []),
  ];
  for (const item of groups) {
    const row = asRecord(item);
    if (!row) continue;
    const a = str(row.a);
    const b = str(row.b);
    const pkg = asRecord(row.package);
    const label = str(pkg?.label_uk) || str(pkg?.theme);
    const rationale = str(pkg?.rationale);
    const status = str(row.status);
    const chips = Array.isArray(row.signal_chips)
      ? row.signal_chips
          .map((c) => str(asRecord(c)?.label_uk))
          .filter(Boolean)
          .join(", ")
      : "";
    const text = [
      `Кандидат МСС: ${shortName(a)} ↔ ${shortName(b)}`,
      status ? `статус: ${status}` : "",
      label,
      rationale,
      chips ? `сигнали: ${chips}` : "",
    ]
      .filter(Boolean)
      .join(". ");
    add({
      name: a,
      short: shortName(a),
      katottg: str(row.a_katottg),
      oblast: "",
      field: "mss_candidate",
      theme: str(pkg?.theme_id) || str(pkg?.theme),
      source: "mss-candidates.json",
      text: `${text} (партнер: ${b})`,
    });
  }
}

function addTwinning(add: Adder, repoRoot: string): void {
  const raw = asRecord(readJson(join(repoRoot, "data/releases/twinning-partners.json")));
  const list = Array.isArray(raw?.hromadas) ? raw.hromadas : [];
  for (const item of list) {
    const row = asRecord(item);
    if (!row) continue;
    const name = str(row.name);
    const partners = Array.isArray(row.partners) ? row.partners : [];
    for (const p of partners) {
      const rec = asRecord(p);
      if (!rec) continue;
      const partner = str(rec.partner_name);
      if (!partner) continue;
      const country = str(rec.partner_country);
      const src = str(rec.source);
      add({
        name,
        short: str(row.short) || shortName(name),
        katottg: str(row.katottg),
        oblast: str(row.oblast),
        field: "twinning",
        theme: country,
        source: "twinning-partners.json",
        text: `Місто-побратим ЄС: ${partner}${country ? ` (${country})` : ""}${src ? `, джерело ${src}` : ""} — не договір МСС за Законом 1508-VII`,
      });
    }
  }
}

function addIntl(add: Adder, repoRoot: string): void {
  const raw = asRecord(readJson(join(repoRoot, "data/releases/intl-agreements.json")));
  const list = Array.isArray(raw?.hromadas) ? raw.hromadas : [];
  for (const item of list) {
    const row = asRecord(item);
    if (!row) continue;
    const name = str(row.name);
    const agreements = Array.isArray(row.agreements) ? row.agreements : [];
    for (const a of agreements) {
      const rec = asRecord(a);
      if (!rec) continue;
      const title = str(rec.title).replace(/\s+/g, " ");
      if (!title) continue;
      add({
        name,
        short: str(row.short) || shortName(name),
        katottg: str(row.katottg),
        oblast: str(row.oblast),
        field: "intl_agreement",
        theme: str(rec.partner_country),
        source: "intl-agreements.json",
        text: `Закон 3668-IX: ${title}. Партнер: ${str(rec.partner_name)} (${str(rec.partner_country)}). Сфера: ${str(rec.sphere)}. Не форма МСС 1508 і не known:true.`,
      });
    }
  }
}

function stripHtmlChrome(html: string): string {
  return html
    .replace(/<script\b[\s\S]*?<\/script>/gi, "\n")
    .replace(/<style\b[\s\S]*?<\/style>/gi, "\n")
    .replace(/<svg\b[\s\S]*?<\/svg>/gi, "\n")
    .replace(/<!--[\s\S]*?-->/g, "\n");
}

function decodeEntities(s: string): string {
  return s
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)));
}

function htmlToPlain(html: string): string {
  return decodeEntities(
    html
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(p|div|h[1-6]|li|tr|section|article|header|blockquote|figcaption)>/gi, "\n")
      .replace(/<[^>]+>/g, " "),
  )
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

function extractBalancedObject(src: string, fromBrace: number): string | null {
  let depth = 0;
  let inStr: string | null = null;
  let escape = false;
  for (let i = fromBrace; i < src.length; i++) {
    const ch = src[i];
    if (inStr) {
      if (escape) {
        escape = false;
        continue;
      }
      if (ch === "\\") {
        escape = true;
        continue;
      }
      if (ch === inStr) inStr = null;
      continue;
    }
    if (ch === '"' || ch === "'") {
      inStr = ch;
      continue;
    }
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return src.slice(fromBrace, i + 1);
    }
  }
  return null;
}

function parsePageI18n(html: string): Record<string, Record<string, string>> | null {
  const marker = html.indexOf("window.PAGE_I18N");
  if (marker < 0) return null;
  const brace = html.indexOf("{", marker);
  if (brace < 0) return null;
  const raw = extractBalancedObject(html, brace);
  if (!raw) return null;
  try {
    return Function(`"use strict"; return (${raw});`)() as Record<string, Record<string, string>>;
  } catch {
    return null;
  }
}

function splitBySize(text: string, max = 1100): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.length <= max) return [trimmed];
  const paras = trimmed.split(/\n\n+/);
  const out: string[] = [];
  let buf = "";
  for (const p of paras) {
    if (buf && buf.length + p.length + 2 > max) {
      out.push(buf.trim());
      buf = p;
    } else {
      buf = buf ? `${buf}\n\n${p}` : p;
    }
  }
  if (buf.trim()) out.push(buf.trim());
  return out.flatMap((s) => {
    if (s.length <= max) return [s];
    const parts: string[] = [];
    for (let i = 0; i < s.length; i += max) parts.push(s.slice(i, i + max));
    return parts;
  });
}

function splitHtmlSections(html: string): { heading: string; body: string }[] {
  const cleaned = stripHtmlChrome(html);
  const headingRe = /<h([1-3])\b[^>]*>([\s\S]*?)<\/h\1>/gi;
  const matches = [...cleaned.matchAll(headingRe)];
  if (matches.length === 0) {
    const plain = htmlToPlain(cleaned);
    return plain ? [{ heading: "", body: plain }] : [];
  }
  const sections: { heading: string; body: string }[] = [];
  const firstIdx = matches[0].index ?? 0;
  const before = htmlToPlain(cleaned.slice(0, firstIdx));
  if (before.length >= MIN_LEN) sections.push({ heading: "", body: before });
  for (let i = 0; i < matches.length; i++) {
    const heading = htmlToPlain(matches[i][2] || "");
    const start = (matches[i].index ?? 0) + matches[i][0].length;
    const end = i + 1 < matches.length ? (matches[i + 1].index ?? cleaned.length) : cleaned.length;
    const body = htmlToPlain(cleaned.slice(start, end));
    if (heading || body.length >= MIN_LEN) sections.push({ heading, body });
  }
  return sections;
}

function splitMarkdownSections(md: string): { heading: string; body: string }[] {
  const text = md.replace(/\r\n/g, "\n").replace(/```[\s\S]*?```/g, " ");
  const sections: { heading: string; body: string[] }[] = [{ heading: "", body: [] }];
  for (const line of text.split("\n")) {
    const m = /^(#{1,3})\s+(.+)$/.exec(line);
    if (m) {
      sections.push({
        heading: m[2].replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").trim(),
        body: [],
      });
    } else {
      sections[sections.length - 1].body.push(line);
    }
  }
  return sections
    .map((s) => ({ heading: s.heading, body: s.body.join("\n").trim() }))
    .filter((s) => s.body.length >= MIN_LEN || s.heading.length >= 3);
}

function pageTitleFromHtml(html: string, fallback: string): string {
  const m = html.match(/<title>([\s\S]*?)<\/title>/i);
  return m ? decodeEntities(m[1]).replace(/\s+/g, " ").trim() : fallback;
}

function addSitePages(add: Adder, repoRoot: string): void {
  const docsDir = join(repoRoot, "docs");
  if (!existsSync(docsDir)) return;
  const files = readdirSync(docsDir)
    .filter((f) => f.endsWith(".html") || f.endsWith(".md"))
    .filter((f) => f !== "hromada-project-passport.html")
    .sort();

  const catalog = files.map((f) => `docs/${f}`).join(", ");
  add({
    name: "Карта сайту",
    short: "сайт",
    katottg: "",
    oblast: "",
    field: "site_page",
    theme: "nav",
    source: "docs/README.md",
    text:
      `Сторінки стейкхолдерського сайту (GitHub Pages, папка docs/): ${catalog}. ` +
      "HTML — публічний інтерфейс; markdown у docs/ — методичні сторінки, теж відкриваються за URL. " +
      "Навігація: Про проєкт (index.html), Кандидати (matches.html), Фонди (funds.html), " +
      "Ресурси (resources.html), Мапа угод МСС (mss-pin-matching-graph.html), AIM-CC експеримент.",
  });

  for (const file of files) {
    const rel = `docs/${file}`;
    const raw = readFileSync(join(docsDir, file), "utf-8");
    const isHtml = file.endsWith(".html");
    const title = isHtml ? pageTitleFromHtml(raw, file) : file.replace(/\.md$/, "");
    const field = isHtml ? "site_page" : "site_doc";
    const sections = isHtml ? splitHtmlSections(raw) : splitMarkdownSections(raw);
    for (const sec of sections) {
      const heading = sec.heading;
      const prefix = `[${rel}] ${title}${heading ? ` — ${heading}` : ""}`;
      for (const part of splitBySize(sec.body)) {
        add({
          name: title,
          short: file,
          katottg: "",
          oblast: "",
          field,
          theme: heading,
          source: rel,
          text: `${prefix}\n${part}`,
        });
      }
    }
    if (isHtml) {
      const i18n = parsePageI18n(raw);
      const en = i18n?.en;
      if (en) {
        const lines = Object.entries(en)
          .filter(([k, v]) => k !== "doc.title" && typeof v === "string" && v.trim().length >= MIN_LEN)
          .map(([, v]) => htmlToPlain(v));
        const blob = lines.join("\n");
        for (const part of splitBySize(blob)) {
          add({
            name: title,
            short: file,
            katottg: "",
            oblast: "",
            field: "site_page",
            theme: "en",
            source: rel,
            text: `[${rel} EN] ${title}\n${part}`,
          });
        }
      }
    }
  }
}

function addInterreg(add: Adder, repoRoot: string): void {
  const raw = asRecord(readJson(join(repoRoot, "data/releases/interreg-partners.json")));
  const list = Array.isArray(raw?.hromadas) ? raw.hromadas : [];
  for (const item of list) {
    const row = asRecord(item);
    if (!row) continue;
    const name = str(row.name);
    const partners = Array.isArray(row.partners) ? row.partners : [];
    for (const p of partners) {
      const rec = asRecord(p);
      if (!rec) continue;
      const project = str(rec.project_name_en) || str(rec.project_acronym);
      if (!project) continue;
      const lpa = rec.is_local_authority === true;
      add({
        name,
        short: str(row.short) || shortName(name),
        katottg: str(row.katottg),
        oblast: str(row.oblast),
        field: "interreg",
        theme: lpa ? "lpa" : str(rec.organisation_type),
        source: "interreg-partners.json",
        text: `Interreg: ${project}. Організація: ${str(rec.partner_name) || str(rec.partner_name_en)} (${str(rec.organisation_type) || "unspecified"}). ${lpa ? "Ймовірно орган місцевої влади." : "Адреса в громаді ≠ рада громади."}`,
      });
    }
  }
}

export function buildTextChunks(repoRoot: string): TextChunk[] {
  const chunks: TextChunk[] = [];
  const add = makeAdder(chunks);
  const skipGoals = addHierarchy(add, repoRoot);
  addHromadas(add, repoRoot, skipGoals);
  addIntents(add, repoRoot);
  addDream(add, repoRoot);
  addCandidates(add, repoRoot);
  addTwinning(add, repoRoot);
  addIntl(add, repoRoot);
  addInterreg(add, repoRoot);
  addSitePages(add, repoRoot);
  return chunks;
}

export function installTextChunks(db: Database.Database, repoRoot: string): ChunkStats {
  const chunks = buildTextChunks(repoRoot);
  db.exec(`DROP TABLE IF EXISTS text_chunks`);
  db.exec(`DROP TABLE IF EXISTS text_chunks_fts`);
  db.exec(`
    CREATE TABLE text_chunks (
      id TEXT PRIMARY KEY,
      name TEXT,
      short TEXT,
      katottg TEXT,
      oblast TEXT,
      field TEXT,
      theme TEXT,
      source TEXT,
      text TEXT
    )
  `);
  db.exec(`
    CREATE VIRTUAL TABLE text_chunks_fts USING fts5(
      text,
      content='text_chunks',
      content_rowid='rowid',
      tokenize = 'unicode61 remove_diacritics 2'
    )
  `);

  const insert = db.prepare(
    `INSERT INTO text_chunks (id, name, short, katottg, oblast, field, theme, source, text)
     VALUES (@id, @name, @short, @katottg, @oblast, @field, @theme, @source, @text)`,
  );
  const tx = db.transaction((rows: TextChunk[]) => {
    for (const row of rows) insert.run(row);
  });
  tx(chunks);
  db.exec(`INSERT INTO text_chunks_fts(text_chunks_fts) VALUES('rebuild')`);

  const byField: Record<string, number> = {};
  for (const c of chunks) byField[c.field] = (byField[c.field] ?? 0) + 1;
  return { total: chunks.length, byField };
}

function tokenizeQuery(query: string): string[] {
  return query
    .replace(/[^\p{L}\p{N}\s-]/gu, " ")
    .split(/\s+/)
    .map((t) => t.trim())
    .filter((t) => t.length >= 2 && !STOP.has(t.toLowerCase()));
}

function extraTerms(query: string): string[] {
  const extra: string[] = [];
  for (const syn of SYNONYMS) {
    if (syn.test.test(query)) extra.push(...syn.extra);
  }
  return extra;
}

function ftsPhrase(term: string): string {
  const cleaned = term.replace(/"/g, "").trim();
  if (!cleaned) return "";
  return `"${cleaned}"*`;
}

function buildMatch(terms: string[], joiner: "AND" | "OR"): string {
  const parts = terms.map(ftsPhrase).filter(Boolean);
  if (parts.length === 0) return "";
  return parts.join(` ${joiner} `);
}

function runMatch(
  db: Database.Database,
  match: string,
  field: string | undefined,
  oblast: string | undefined,
  katottg: string | undefined,
  limit: number,
): ChunkHit[] {
  if (!match) return [];
  const where: string[] = ["text_chunks_fts MATCH ?"];
  const args: unknown[] = [match];
  if (field) {
    const fields = field.split(",").map((f) => f.trim()).filter(Boolean);
    if (fields.length === 1) {
      where.push("text_chunks.field = ?");
      args.push(fields[0]);
    } else if (fields.length > 1) {
      where.push(`text_chunks.field IN (${fields.map(() => "?").join(",")})`);
      args.push(...fields);
    }
  }
  if (oblast) {
    where.push("text_chunks.oblast LIKE ?");
    args.push(`%${oblast}%`);
  }
  if (katottg) {
    where.push("text_chunks.katottg = ?");
    args.push(katottg);
  }
  args.push(limit);
  const sql = `
    SELECT
      text_chunks.name AS name,
      text_chunks.short AS short,
      text_chunks.katottg AS katottg,
      text_chunks.oblast AS oblast,
      text_chunks.field AS field,
      text_chunks.theme AS theme,
      text_chunks.source AS source,
      snippet(text_chunks_fts, 0, '«', '»', '…', 28) AS text,
      text_chunks_fts.rank AS rank
    FROM text_chunks_fts
    JOIN text_chunks ON text_chunks.rowid = text_chunks_fts.rowid
    WHERE ${where.join(" AND ")}
    ORDER BY rank
    LIMIT ?
  `;
  try {
    return db.prepare(sql).all(...args) as ChunkHit[];
  } catch {
    return [];
  }
}

export function searchTextChunks(
  db: Database.Database,
  opts: {
    query: string;
    field?: string;
    oblast?: string;
    katottg?: string;
    limit?: number;
  },
): { query_used: string; hits: ChunkHit[] } {
  const limit = Math.min(Math.max(opts.limit ?? 12, 1), 30);
  const tokens = tokenizeQuery(opts.query);
  const extras = extraTerms(opts.query);
  const andTerms = tokens.length > 0 ? tokens : extras.slice(0, 3);
  const orTerms = [...new Set([...tokens, ...extras])];

  const andMatch = buildMatch(andTerms, "AND");
  let hits = runMatch(db, andMatch, opts.field, opts.oblast, opts.katottg, limit);
  let used = andMatch;
  if (hits.length < 3 && orTerms.length > 1) {
    const orMatch = buildMatch(orTerms, "OR");
    const more = runMatch(db, orMatch, opts.field, opts.oblast, opts.katottg, limit);
    if (more.length > hits.length) {
      hits = more;
      used = orMatch;
    }
  }
  return { query_used: used, hits };
}
