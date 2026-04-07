import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const outputDir = path.join(projectRoot, "capacitor-www");

const fallbackHealthUrl = "https://bounswe2026group2-backend-dev.onrender.com/health";
const rawApiInput = process.env.MOBILE_API_BASE_URL || fallbackHealthUrl;
const apiBase = rawApiInput.replace(/\/health\/?$/i, "").replace(/\/$/, "");

const copyExtensions = new Set([
  ".html",
  ".js",
  ".css",
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".svg",
  ".webp",
  ".ico",
  ".json"
]);

rmSync(outputDir, { recursive: true, force: true });
mkdirSync(outputDir, { recursive: true });

for (const dirent of readdirSync(projectRoot, { withFileTypes: true })) {
  if (!dirent.isFile()) {
    continue;
  }

  const ext = path.extname(dirent.name).toLowerCase();
  if (!copyExtensions.has(ext)) {
    continue;
  }

  const src = path.join(projectRoot, dirent.name);
  const dest = path.join(outputDir, dirent.name);
  cpSync(src, dest);
}

const configPath = path.join(outputDir, "config.js");
if (!existsSync(configPath)) {
  throw new Error("config.js was not copied into capacitor-www.");
}

const configContents = readFileSync(configPath, "utf8").replace(/__API_BASE_URL__/g, apiBase);
writeFileSync(configPath, configContents, "utf8");

console.log(`Prepared ${outputDir} with API base ${apiBase}`);
