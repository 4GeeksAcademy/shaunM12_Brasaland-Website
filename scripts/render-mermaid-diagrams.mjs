#!/usr/bin/env node
/**
 * Render docs/diagrams/mermaid/*.mmd to PNG.
 *
 * 1. Tries @mermaid-js/mermaid-cli (mmdc + Puppeteer) when Chrome deps exist.
 * 2. Falls back to mermaid.ink (no local Chrome required).
 *
 * Run: npm run diagrams:render
 */
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const mmdDir = join(root, "docs/diagrams/mermaid");
const mmdc = join(root, "node_modules/.bin/mmdc");

const files = readdirSync(mmdDir).filter((name) => name.endsWith(".mmd"));

function renderViaMermaidInk(source, outputPath) {
  const payload = Buffer.from(
    JSON.stringify({ code: source, mermaid: { theme: "default" } }),
  ).toString("base64url");
  execFileSync(
    "curl",
    ["-fsSL", `https://mermaid.ink/img/${payload}`, "-o", outputPath],
    { stdio: "inherit" },
  );
}

function renderViaMmdc(input, output) {
  execFileSync(
    mmdc,
    ["-i", input, "-o", output, "-b", "white", "-w", "1200", "-H", "900"],
    { stdio: "pipe", cwd: root },
  );
}

let usedRemote = false;

for (const file of files) {
  const input = join(mmdDir, file);
  const output = join(mmdDir, file.replace(/\.mmd$/, ".png"));
  const source = readFileSync(input, "utf8");
  console.log(`Rendering ${file} → ${file.replace(/\.mmd$/, ".png")}`);

  try {
    renderViaMmdc(input, output);
  } catch {
    console.warn(`  mmdc failed for ${file}; using mermaid.ink fallback…`);
    renderViaMermaidInk(source, output);
    usedRemote = true;
  }
}

if (usedRemote) {
  console.log(
    "Note: mermaid.ink fallback used. For offline renders, install Chrome deps and re-run.",
  );
}
console.log(`Done — ${files.length} diagram(s) in docs/diagrams/mermaid/`);
