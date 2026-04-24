/**
 * One-off UI capture: npx playwright install chromium (once), then:
 * node scripts/capture-ui-screenshots.mjs
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "ui-screenshots");
const BASE = process.env.PORTAL_BASE_URL ?? "http://localhost:3001";

const ROUTES = [
  { file: "00-home", path: "/" },
  { file: "01-dashboard", path: "/dashboard" },
  { file: "02-discover", path: "/discover" },
  { file: "03-run", path: "/run" },
  { file: "04-agents", path: "/agents" },
  { file: "05-agents-new", path: "/agents/new" },
  { file: "06-teams", path: "/teams" },
  { file: "07-teams-new", path: "/teams/new" },
  { file: "08-protocols", path: "/protocols" },
  { file: "09-pipelines", path: "/pipelines" },
  { file: "10-pipelines-new", path: "/pipelines/new" },
  { file: "11-integrations", path: "/integrations" },
  { file: "12-knowledge", path: "/knowledge" },
  { file: "13-runs", path: "/runs" },
  { file: "14-corrections", path: "/corrections" },
];

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  for (const { file, path } of ROUTES) {
    const url = `${BASE}${path}`;
    process.stderr.write(`${url} -> ${file}.png\n`);
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
      await page.waitForTimeout(800);
      await page.screenshot({
        path: join(OUT, `${file}.png`),
        fullPage: true,
      });
    } catch (e) {
      process.stderr.write(`  ERROR: ${e.message}\n`);
    }
  }

  await browser.close();
  process.stdout.write(`Done. Wrote ${ROUTES.length} images under ${OUT}\n`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
