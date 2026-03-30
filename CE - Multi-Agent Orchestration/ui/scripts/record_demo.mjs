import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { chromium } from 'playwright'

const UI_URL = process.env.UI_URL || 'http://localhost:5173'
const OUT_DIR = path.resolve(process.cwd(), 'demo_artifacts')
const VIDEO_DIR = path.join(OUT_DIR, 'video_tmp')
const DOWNLOADS_DIR = path.join(OUT_DIR, 'downloads')

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

async function expectVisible(page, locator, label) {
  await locator.waitFor({ state: 'visible', timeout: 30_000 })
  // Guard against clicks landing on detached nodes
  await page.waitForTimeout(200)
  return locator
}

async function nav(page, route) {
  await page.goto(`${UI_URL}${route}`, { waitUntil: 'domcontentloaded' })
}

async function pickFirstProtocol(page) {
  const select = page.locator('select').first()
  await expectVisible(page, select, 'protocol select')

  // If only placeholder exists, backend isn't serving protocols yet.
  const options = await select.locator('option').all()
  if (options.length < 2) {
    throw new Error('No protocols loaded in Run view. Is the API running and CORS configured?')
  }

  // Prefer Parallel Synthesis if present, otherwise the first real option.
  const preferred = await select.locator('option', { hasText: /Parallel Synthesis|p03_parallel_synthesis/i }).count()
  if (preferred > 0) {
    const value = await select.locator('option', { hasText: /Parallel Synthesis|p03_parallel_synthesis/i }).first().getAttribute('value')
    await select.selectOption(value || undefined)
    return
  }

  const value = await options[1].getAttribute('value')
  await select.selectOption(value || undefined)
}

async function runProtocolAndDownloadPdf(page, runLabel) {
  await expectVisible(page, page.getByRole('button', { name: 'Run Protocol' }), 'Run Protocol button')
  await page.getByRole('button', { name: 'Run Protocol' }).click()

  // Wait for completion status and PDF button.
  await page.getByText('Completed', { exact: false }).waitFor({ timeout: 10 * 60_000 })
  return await downloadPdf(page, runLabel)
}

async function downloadPdf(page, runLabel) {
  await expectVisible(page, page.getByRole('button', { name: 'Download PDF' }), 'Download PDF button')

  const downloadPromise = page.waitForEvent('download', { timeout: 60_000 })
  await page.getByRole('button', { name: 'Download PDF' }).click()
  const download = await downloadPromise

  const suggested = download.suggestedFilename()
  const outName = `${runLabel}-${suggested}`.replaceAll(/[^a-zA-Z0-9._-]+/g, '-')
  const outPath = path.join(DOWNLOADS_DIR, outName)
  await download.saveAs(outPath)
  return outPath
}

async function main() {
  ensureDir(OUT_DIR)
  ensureDir(VIDEO_DIR)
  ensureDir(DOWNLOADS_DIR)

  const browser = await chromium.launch({
    headless: true,
  })

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
    acceptDownloads: true,
  })

  const page = await context.newPage()

  // ── 1) Create an agent ─────────────────────────────────────────────────────
  await nav(page, '/agents')
  await expectVisible(page, page.getByRole('button', { name: 'Create Agent' }), 'Create Agent button')
  await page.getByRole('button', { name: 'Create Agent' }).click()

  await expectVisible(page, page.getByText('Identity', { exact: true }), 'AgentEditor Identity section')
  await page.getByText('Name', { exact: true }).locator('..').locator('input').fill('Demo Strategy Analyst')
  await page.getByText('Key', { exact: true }).locator('..').locator('input').fill('demo-strategy-analyst')

  // Minimal system prompt so it’s non-empty and looks real.
  await page.getByText('System Prompt', { exact: true }).locator('..').locator('textarea').fill(
    [
      'You are a strategy analyst for Cardinal Element.',
      'Provide crisp, operator-grade analysis with clear recommendations, risks, and next actions.',
      'If asked to produce a deliverable, output a structured brief.',
    ].join('\n')
  )

  await page.getByRole('button', { name: 'Save' }).click()

  // ── 2) Add agent to team + save team ───────────────────────────────────────
  // Ensure the newly created agent appears in list; search and select.
  await expectVisible(page, page.getByPlaceholder('Search agents...'), 'Agent search')
  await page.getByPlaceholder('Search agents...').fill('Demo Strategy Analyst')
  await page.getByRole('button', { name: /Demo Strategy Analyst/i }).click()
  await expectVisible(page, page.getByRole('button', { name: 'Add to Team' }), 'Add to Team button')
  await page.getByRole('button', { name: 'Add to Team' }).click()

  await nav(page, '/teams')
  await expectVisible(page, page.getByText('Team Composition', { exact: true }), 'Teams page header')
  await page.locator('input[type="text"]').first().fill('Demo Team')
  await page.getByPlaceholder('Team description (optional)').fill('A minimal team for the product demo flow.')
  await page.getByRole('button', { name: /Save Team|Update Team/i }).click()

  // ── 3) Run a protocol ──────────────────────────────────────────────────────
  await nav(page, '/run')
  await expectVisible(page, page.getByText('Run Protocol', { exact: true }), 'Run Protocol panel')
  await pickFirstProtocol(page)
  await page.getByPlaceholder('What strategic question should the team analyze?').fill(
    'We’re a boutique consultancy considering productizing our audit into a repeatable offering. What should we do in the next 30 days?'
  )

  const protocolPdf = await runProtocolAndDownloadPdf(page, 'protocol')

  // ── 4) Create and run a pipeline ───────────────────────────────────────────
  await nav(page, '/pipelines')
  await expectVisible(page, page.getByText('Pipeline Builder', { exact: false }), 'Pipelines page header')

  // Step 1 protocol select + prompt.
  const step1Select = page.locator('select').first()
  await step1Select.selectOption({ index: 1 })
  await page.locator('textarea').first().fill('Summarize the decision options and constraints for: {question}')

  // Add step, set step 2.
  await page.getByRole('button', { name: 'Add step' }).first().click()
  const selects = page.locator('select')
  await selects.nth(1).selectOption({ index: 1 })
  const textareas = page.locator('textarea')
  await textareas.nth(1).fill('Given {prev_output}, produce a prioritized 30-day plan with owners and risks.')

  await page.getByRole('button', { name: 'Save Pipeline' }).click()

  // Run the saved pipeline (first card).
  await expectVisible(page, page.getByText('Saved Pipelines', { exact: false }), 'Saved Pipelines section')
  await page.getByRole('button', { name: 'Run' }).first().click()
  await expectVisible(page, page.getByPlaceholder('What strategic question should the pipeline analyze?'), 'Pipeline run modal question')
  await page.getByPlaceholder('What strategic question should the pipeline analyze?').fill(
    'Should we expand Cardinal Element into a product + services hybrid model?'
  )
  await page.getByRole('button', { name: 'Start Pipeline' }).click()

  // RunView auto-starts; wait for completion then download PDF.
  await page.getByText('Completed', { exact: false }).waitFor({ timeout: 15 * 60_000 })
  const pipelinePdf = await downloadPdf(page, 'pipeline')

  // Close to flush video.
  await context.close()
  await browser.close()

  // Move the newest recorded video to a stable filename.
  const videos = fs.readdirSync(VIDEO_DIR).filter((f) => f.endsWith('.webm') || f.endsWith('.mp4'))
  if (videos.length === 0) {
    throw new Error('No video produced. (Playwright did not emit a recordVideo file.)')
  }
  // Pick most recent.
  const newest = videos
    .map((f) => ({ f, t: fs.statSync(path.join(VIDEO_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t)[0].f

  const src = path.join(VIDEO_DIR, newest)
  const dst = path.join(OUT_DIR, 'ce-orchestrator-demo.webm')
  fs.copyFileSync(src, dst)

  console.log('Demo artifacts written:')
  console.log(`- Video: ${dst}`)
  console.log(`- Protocol PDF: ${protocolPdf}`)
  console.log(`- Pipeline PDF: ${pipelinePdf}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
