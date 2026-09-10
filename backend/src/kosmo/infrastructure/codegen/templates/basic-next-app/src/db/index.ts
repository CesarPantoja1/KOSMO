import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import * as schema from "./schema";

function openSqliteDatabase(): Database.Database {
  const rawPath =
    process.env.DATABASE_URL ||
    process.env.DATABASE_PATH ||
    path.join(process.cwd(), ".data", "sqlite.db");
  const cleanPath = rawPath.replace(/^file:\/\//, "").replace(/^file:/, "");

  try {
    const dir = path.dirname(cleanPath);
    if (dir && dir !== "." && !fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    return new Database(cleanPath);
  } catch (err) {
    console.warn(`[db] No se pudo abrir base de datos en '${cleanPath}':`, err);
    return new Database(":memory:");
  }
}

export const sqlite = openSqliteDatabase();
export const db = drizzle(sqlite, { schema });
