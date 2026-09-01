import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as schema from "./schema";

const rawPath = process.env.DATABASE_URL || process.env.DATABASE_PATH || "sqlite.db";
const dbPath = rawPath.replace(/^file:\/\//, "").replace(/^file:/, "");
const sqlite = new Database(dbPath);
export const db = drizzle(sqlite, { schema });
