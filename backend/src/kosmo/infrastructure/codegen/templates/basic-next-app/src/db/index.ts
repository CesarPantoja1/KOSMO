import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import * as schema from "./schema";

function openSqliteDatabase(): Database.Database {
  const rawPath = process.env.DATABASE_URL || process.env.DATABASE_PATH || "sqlite.db";
  const cleanPath = rawPath.replace(/^file:\/\//, "").replace(/^file:/, "");

  const candidates = [
    cleanPath,
    path.join(process.cwd(), "sqlite.db"),
    "/tmp/sqlite.db",
  ];

  for (const candidate of candidates) {
    try {
      const dir = path.dirname(candidate);
      if (dir && dir !== "." && !fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      return new Database(candidate);
    } catch (err) {
      console.warn(`[db] No se pudo abrir base de datos en '${candidate}':`, err);
    }
  }

  return new Database(":memory:");
}

export const sqlite = openSqliteDatabase();
export const db = drizzle(sqlite, { schema });
