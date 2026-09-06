/**
 * Loads data/releases/*.json into an in-memory SQLite database so it can be
 * queried with arbitrary SQL. Generic on purpose — no per-file special-casing:
 *
 *   - a root-array file (hromadas.json) becomes one table
 *   - a root-object file (edem-barometer.json) contributes one table per
 *     top-level array field (`edem_barometer__hromadas`), and its remaining
 *     scalar fields (generatedAt, method, warning, coverage, …) land in `_meta`
 *   - nested objects/arrays inside a row are kept as JSON text columns
 *     (query them with SQLite's json_extract / json_each)
 */

import Database from "better-sqlite3";
import { readFileSync, readdirSync } from "fs";
import { basename, join } from "path";

export interface ColumnInfo {
  name: string;
  type: "INTEGER" | "REAL" | "TEXT";
}

export interface TableInfo {
  name: string;
  sourceFile: string;
  sourceKey?: string;
  rowCount: number;
  columns: ColumnInfo[];
}

function sanitizeName(raw: string): string {
  const cleaned = raw.replace(/[^a-zA-Z0-9_]/g, "_").replace(/^_+|_+$/g, "");
  return cleaned.length > 0 ? cleaned : "t";
}

function classifyColumnType(values: unknown[]): ColumnInfo["type"] {
  let sawObjectLike = false;
  let sawString = false;
  let sawBool = false;
  let sawNonIntNumber = false;
  let sawNumber = false;
  let any = false;

  for (const v of values) {
    if (v === null || v === undefined) continue;
    any = true;
    const t = typeof v;
    if (t === "object") {
      sawObjectLike = true;
    } else if (t === "string") {
      sawString = true;
    } else if (t === "boolean") {
      sawBool = true;
    } else if (t === "number") {
      sawNumber = true;
      if (!Number.isInteger(v)) sawNonIntNumber = true;
    }
  }

  if (!any) return "TEXT";
  if (sawObjectLike || sawString) return "TEXT";
  if (sawBool && !sawNumber) return "INTEGER";
  if (sawNumber) return sawNonIntNumber ? "REAL" : "INTEGER";
  return "TEXT";
}

function toStorable(value: unknown, colType: ColumnInfo["type"]): unknown {
  if (value === null || value === undefined) return null;
  if (typeof value === "object") return JSON.stringify(value);
  if (colType === "TEXT" && typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (colType === "INTEGER" && typeof value === "boolean") {
    return value ? 1 : 0;
  }
  return value;
}

function createTableFromArray(
  db: Database.Database,
  tableName: string,
  rows: unknown[],
  sourceFile: string,
  sourceKey?: string,
): TableInfo {
  const isObjectArray = rows.every(
    (r) => r !== null && typeof r === "object" && !Array.isArray(r),
  );

  let columnNames: string[];
  let getRowValues: (row: unknown) => Record<string, unknown>;

  if (isObjectArray) {
    const seen = new Set<string>();
    const order: string[] = [];
    for (const row of rows as Record<string, unknown>[]) {
      for (const key of Object.keys(row)) {
        if (!seen.has(key)) {
          seen.add(key);
          order.push(key);
        }
      }
    }
    columnNames = order;
    getRowValues = (row) => row as Record<string, unknown>;
  } else {
    columnNames = ["value"];
    getRowValues = (row) => ({ value: row });
  }

  const colTypes: Record<string, ColumnInfo["type"]> = {};
  for (const col of columnNames) {
    colTypes[col] = classifyColumnType(rows.map((r) => getRowValues(r)[col]));
  }

  const columnsDdl = columnNames.map((c) => `"${c}" ${colTypes[c]}`).join(", ");
  db.exec(`CREATE TABLE "${tableName}" (${columnsDdl})`);

  const insertStmt = db.prepare(
    `INSERT INTO "${tableName}" (${columnNames.map((c) => `"${c}"`).join(", ")}) VALUES (${columnNames.map(() => "?").join(", ")})`,
  );
  const insertMany = db.transaction((data: unknown[]) => {
    for (const row of data) {
      const rowValues = getRowValues(row);
      insertStmt.run(...columnNames.map((c) => toStorable(rowValues[c], colTypes[c])));
    }
  });
  insertMany(rows);

  return {
    name: tableName,
    sourceFile,
    sourceKey,
    rowCount: rows.length,
    columns: columnNames.map((c) => ({ name: c, type: colTypes[c] })),
  };
}

export interface LoadedDb {
  db: Database.Database;
  tables: TableInfo[];
  releasesDir: string;
}

export function loadReleasesIntoDb(repoRoot: string): LoadedDb {
  const db = new Database(":memory:");
  const releasesDir = join(repoRoot, "data", "releases");
  const files = readdirSync(releasesDir)
    .filter((f) => f.endsWith(".json") && !f.endsWith(".manifest.json"))
    .sort();

  const tables: TableInfo[] = [];
  const metaRows: { sourceFile: string; meta: Record<string, unknown> }[] = [];

  for (const file of files) {
    const relPath = `data/releases/${file}`;
    const stem = sanitizeName(basename(file, ".json"));
    let parsed: unknown;
    try {
      parsed = JSON.parse(readFileSync(join(releasesDir, file), "utf-8"));
    } catch {
      continue;
    }

    if (Array.isArray(parsed)) {
      if (parsed.length === 0) continue;
      tables.push(createTableFromArray(db, stem, parsed, relPath));
      continue;
    }

    if (parsed && typeof parsed === "object") {
      const obj = parsed as Record<string, unknown>;
      const metaFields: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(obj)) {
        if (Array.isArray(value) && value.length > 0) {
          const tableName = `${stem}__${sanitizeName(key)}`;
          tables.push(createTableFromArray(db, tableName, value, relPath, key));
        } else {
          metaFields[key] = value;
        }
      }
      if (Object.keys(metaFields).length > 0) {
        metaRows.push({ sourceFile: relPath, meta: metaFields });
      }
    }
  }

  db.exec(`CREATE TABLE _meta (source_file TEXT PRIMARY KEY, meta_json TEXT)`);
  const insertMeta = db.prepare(`INSERT INTO _meta (source_file, meta_json) VALUES (?, ?)`);
  const metaTx = db.transaction((rows: typeof metaRows) => {
    for (const r of rows) insertMeta.run(r.sourceFile, JSON.stringify(r.meta));
  });
  metaTx(metaRows);

  return { db, tables, releasesDir };
}
