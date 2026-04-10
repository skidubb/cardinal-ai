import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { pathToFileURL } from 'node:url'
import { chromium } from 'playwright'

const UI_URL = process.env.UI_URL || 'https://cardinal-ai-production.up.railway.app'
const PASSWORD = process.env.DEMO_PASSWORD || 'cardinal'

/** Pause between major beats so viewers can follow (ms). Override: DEMO_BEAT_MS */
const BEAT_MS = Number.parseInt(process.env.DEMO_BEAT_MS || '4500', 10)
/** Extra hold after big transitions (ms). Override: DEMO_HOLD_MS */
const HOLD_MS = Number.parseInt(process.env.DEMO_HOLD_MS || '5500', 10)
/** After a failed run, keep error on screen (ms). Override: DEMO_ERROR_HOLD_MS */
const ERROR_HOLD_MS = Number.parseInt(process.env.DEMO_ERROR_HOLD_MS || '14000', 10)
/** Slight delay on every Playwright action (ms). Override: DEMO_SLOW_MO */
const SLOW_MO_MS = Number.parseInt(process.env.DEMO_SLOW_MO || '120', 10)
/** Typing delay per character for visible fields (ms). Override: DEMO_TYPE_DELAY */
const TYPE_DELAY_MS = Number.parseInt(process.env.DEMO_TYPE_DELAY || '35', 10)
/** How long to keep the local PDF open in the browser after download (ms). Override: DEMO_PDF_VIEW_MS */
const PDF_VIEW_MS = Number.parseInt(process.env.DEMO_PDF_VIEW_MS || '22000', 10)

const OUT_DIR = path.resolve(process.cwd(), 'demo_artifacts_hosted')
const VIDEO_DIR = path.join(OUT_DIR, 'video_tmp')
const DOWNLOADS_DIR = path.join(OUT_DIR, 'downloads')

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

async function dwell(page, ms, _reason = '') {
  await page.waitForTimeout(ms)
}

async function beat(page, _reason = '') {
  await page.waitForTimeout(BEAT_MS)
}

/** Clear field then type with per-key delay (readable on video). */
async function humanType(locator, text, label) {
  await expectVisible(locator, label)
  await locator.click()
  await locator.fill('')
  await locator.pressSequentially(text, { delay: TYPE_DELAY_MS })
}

async function expectVisible(locator, label) {
  await locator.waitFor({ state: 'visible', timeout: 45_000 })
  return locator
}

async function safeClick(locator, label) {
  await expectVisible(locator, label)
  await locator.click({ timeout: 45_000 })
}

async function sidebarGo(page, label) {
  const link = page.getByRole('link', { name: label, exact: true })
  if (await link.count()) {
    await safeClick(link, `sidebar link: ${label}`)
    await beat(page, `after nav ${label}`)
    return
  }
  // Fallback for cases where sidebar isn't present (or nav labels differ):
  // go directly to route and rely on SPA routing.
  const routeByLabel = {
    Dashboard: '/dashboard',
    Agents: '/agents',
    Teams: '/teams',
    Protocols: '/protocols',
    Pipelines: '/pipelines',
    Run: '/run',
  }
  const route = routeByLabel[label] || '/'
  await page.goto(`${UI_URL}${route}`, { waitUntil: 'networkidle' }).catch(() =>
    page.goto(`${UI_URL}${route}`, { waitUntil: 'domcontentloaded' })
  )
  await beat(page, `after goto ${route}`)
}

async function loginIfNeeded(page) {
  // Hosted app uses LoginGate password.
  const passwordInput = page.getByPlaceholder('Password')
  if (await passwordInput.count()) {
    await expectVisible(passwordInput, 'login password input')
    await passwordInput.fill(PASSWORD)
    await safeClick(page.getByRole('button', { name: 'Sign In' }), 'Sign In button')
    // Wait for sidebar to appear.
    await page.getByRole('link', { name: 'Dashboard', exact: true }).waitFor({ timeout: 45_000 })
  }

  // If already authenticated, still wait for app chrome to be ready.
  await page.getByRole('link', { name: 'Dashboard', exact: true }).waitFor({ timeout: 45_000 })
  await dwell(page, HOLD_MS, 'login / app shell')
}

async function pickProtocol(page, protocolKey = 'p03_parallel_synthesis') {
  const select = page.locator('select').first()
  await expectVisible(select, 'protocol select')
  const has = await select.locator(`option[value="${protocolKey}"]`).count()
  if (has > 0) {
    await select.selectOption(protocolKey)
    return
  }
  // Fallback: first non-placeholder option.
  await select.selectOption({ index: 1 })
}

/** Returns 'completed' | 'failed' — never throws (so we still save the screen recording). */
async function waitForRunEnd(page, timeoutMs) {
  const completed = page.getByText('Completed', { exact: false }).waitFor({ timeout: timeoutMs })
  const failed = page.getByText('Failed', { exact: false }).waitFor({ timeout: timeoutMs })
  await Promise.race([completed, failed])
  const failedVisible = await page.getByText('Failed', { exact: false }).first().isVisible().catch(() => false)
  return failedVisible ? 'failed' : 'completed'
}

async function downloadPdfIfPossible(page, label) {
  const btn = page.getByRole('button', { name: 'Download PDF' })
  if (!(await btn.count())) return null
  try {
    await expectVisible(btn, 'Download PDF button')
    const downloadPromise = page.waitForEvent('download', { timeout: 120_000 })
    await btn.click()
    const download = await downloadPromise
    const outName = `${label}-${download.suggestedFilename()}`.replaceAll(/[^a-zA-Z0-9._-]+/g, '-')
    const outPath = path.join(DOWNLOADS_DIR, outName)
    await download.saveAs(outPath)
    return outPath
  } catch {
    console.warn(`[hosted-demo] PDF download skipped or timed out (${label})`)
    return null
  }
}

/** Open a saved PDF in Chromium’s built-in viewer so the recording shows the document. */
async function showPdfInRecording(page, absPath, reason) {
  if (!absPath || !fs.existsSync(absPath)) return
  const url = pathToFileURL(absPath).href
  console.log(`[hosted-demo] opening PDF in browser (${reason}): ${url}`)
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 })
  await dwell(page, Math.floor(PDF_VIEW_MS * 0.25), 'pdf first page')
  // Gentle scroll so viewers see more than the top margin.
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 450)
    await page.waitForTimeout(900)
  }
  await dwell(page, Math.floor(PDF_VIEW_MS * 0.35), 'pdf content')
}

function finalizeVideoFromTemp() {
  const vids = fs.readdirSync(VIDEO_DIR).filter((f) => f.endsWith('.webm') || f.endsWith('.mp4'))
  if (vids.length === 0) return null
  const newest = vids
    .map((f) => ({ f, t: fs.statSync(path.join(VIDEO_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t)[0].f
  const src = path.join(VIDEO_DIR, newest)
  const dst = path.join(OUT_DIR, 'ce-orchestrator-demo-hosted.webm')
  fs.copyFileSync(src, dst)
  return dst
}

async function main() {
  ensureDir(OUT_DIR)
  ensureDir(VIDEO_DIR)
  ensureDir(DOWNLOADS_DIR)

  const demoId = String(Math.floor(Date.now() / 1000))
  const agentName = `Demo Strategy Analyst ${demoId}`
  const agentKey = `demo-strategy-analyst-${demoId}`
  const teamName = `Demo Team ${demoId}`
  const pipelineName = `Demo Pipeline ${demoId}`

  console.log(`[hosted-demo] starting (id=${demoId})`)
  console.log(`[hosted-demo] pace: slowMo=${SLOW_MO_MS}ms beat=${BEAT_MS}ms hold=${HOLD_MS}ms errorHold=${ERROR_HOLD_MS}ms typeDelay=${TYPE_DELAY_MS}ms`)

  const browser = await chromium.launch({ headless: true, slowMo: SLOW_MO_MS })
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
    acceptDownloads: true,
  })
  const page = await context.newPage()

  let protocolPdf = null
  let pipelinePdf = null
  let protocolEnd = null
  let pipelineEnd = null

  try {
    // Land on protocols (as requested) but we’ll navigate via sidebar for the full story.
    await page.goto(`${UI_URL}/protocols`, { waitUntil: 'networkidle' }).catch(() =>
      page.goto(`${UI_URL}/protocols`, { waitUntil: 'domcontentloaded' })
    )
    await loginIfNeeded(page)
    await dwell(page, HOLD_MS, 'protocols landing')

    console.log('[hosted-demo] create agent')
    await sidebarGo(page, 'Agents')
    await dwell(page, HOLD_MS, 'agent registry')
    await safeClick(page.getByRole('button', { name: 'Create Agent' }), 'Create Agent')
    await expectVisible(page.getByText('Identity', { exact: true }), 'Agent editor')
    await dwell(page, BEAT_MS, 'editor open')

    const nameInput = page.getByText('Name', { exact: true }).locator('..').locator('input')
    const keyInput = page.getByText('Key', { exact: true }).locator('..').locator('input')
    const promptBox = page.getByText('System Prompt', { exact: true }).locator('..').locator('textarea')
    await humanType(nameInput, agentName, 'name')
    await beat(page)
    await humanType(keyInput, agentKey, 'key')
    await beat(page)
    await humanType(
      promptBox,
      [
        'You are a strategy analyst for Cardinal Element.',
        'Give crisp recommendations, risks, and next actions.',
        'Return structured output suitable for a client-ready brief.',
      ].join('\n'),
      'prompt'
    )
    await dwell(page, HOLD_MS, 'review agent form')
    await safeClick(page.getByRole('button', { name: 'Save' }), 'Save agent')
    await beat(page, 'after save agent')
    if (await page.locator('.fixed.inset-0.z-50').count()) {
      const close = page.getByRole('button', { name: '×' })
      if (await close.count()) await close.first().click()
      await page.waitForTimeout(300)
    }

    console.log('[hosted-demo] create team')
    await sidebarGo(page, 'Teams')
    await expectVisible(page.getByText('Team Composition', { exact: true }), 'Teams page')

    const addTeamAgent = async (needle) => {
      const filter = page.getByPlaceholder('Filter agents by name or category...')
      await humanType(filter, needle, `team filter ${needle}`)
      const btn = page.getByRole('button', { name: new RegExp(`\\+\\s*.*${needle}.*`, 'i') }).first()
      await safeClick(btn, `add agent ${needle}`)
      await beat(page, `after add ${needle}`)
    }
    await addTeamAgent('CEO')
    await addTeamAgent('CFO')
    await addTeamAgent('CTO')

    await humanType(page.locator('input[type="text"]').first(), teamName, 'team name')
    await beat(page)
    await humanType(
      page.getByPlaceholder('Team description (optional)'),
      'A minimal demo team (CEO/CFO/CTO).',
      'team description'
    )
    await dwell(page, HOLD_MS, 'review team')
    await safeClick(page.getByRole('button', { name: /Save Team|Update Team/i }), 'Save team')
    await beat(page, 'after save team')

    console.log('[hosted-demo] run protocol')
    await sidebarGo(page, 'Run')
    await expectVisible(page.getByRole('heading', { name: 'Run Protocol' }), 'Run view')
    await dwell(page, HOLD_MS, 'run form visible')
    await pickProtocol(page, 'p03_parallel_synthesis')
    await beat(page, 'after protocol select')
    const q1 = page.getByPlaceholder('What strategic question should the team analyze?')
    await humanType(
      q1,
      'We’re a boutique consultancy considering productizing our audit into a repeatable offering. What should we do in the next 30 days?',
      'strategic question'
    )
    await dwell(page, HOLD_MS, 'before run protocol')
    await safeClick(page.getByRole('button', { name: 'Run Protocol' }), 'Run Protocol')
    protocolEnd = await waitForRunEnd(page, 15 * 60_000)
    console.log(`[hosted-demo] protocol ended: ${protocolEnd}`)
    if (protocolEnd === 'completed') {
      protocolPdf = await downloadPdfIfPossible(page, 'protocol')
      await dwell(page, HOLD_MS, 'after protocol success')
    } else {
      await dwell(page, ERROR_HOLD_MS, 'protocol error on screen')
    }

    console.log('[hosted-demo] build + run pipeline')
    await sidebarGo(page, 'Pipelines')
    await expectVisible(page.getByText('Pipeline Builder', { exact: false }), 'Pipelines page')
    await dwell(page, HOLD_MS, 'pipeline builder')
    await humanType(page.locator('input[type="text"]').first(), pipelineName, 'pipeline name')
    await beat(page)

    const step1Select = page.locator('select').first()
    await step1Select.selectOption('p03_parallel_synthesis').catch(async () => step1Select.selectOption({ index: 1 }))
    await beat(page)
    await humanType(
      page.locator('textarea').first(),
      'Summarize the decision options and constraints for: {question}',
      'step1 template'
    )
    await dwell(page, BEAT_MS, 'step 1')

    await safeClick(page.getByRole('button', { name: 'Add step' }).first(), 'Add step')
    await beat(page)
    const selects = page.locator('select')
    await selects.nth(1).selectOption('p03_parallel_synthesis').catch(async () => selects.nth(1).selectOption({ index: 1 }))
    await beat(page)
    const textareas = page.locator('textarea')
    await humanType(
      textareas.nth(1),
      'Given {prev_output}, produce a prioritized 30-day plan with owners and risks.',
      'step2 template'
    )
    await dwell(page, HOLD_MS, 'review pipeline')

    await safeClick(page.getByRole('button', { name: 'Save Pipeline' }), 'Save Pipeline')
    await beat(page, 'after save pipeline')

    await expectVisible(page.getByText('Saved Pipelines', { exact: false }), 'Saved Pipelines')
    await dwell(page, HOLD_MS, 'saved pipelines list')
    await safeClick(page.getByRole('button', { name: 'Run' }).first(), 'Run pipeline (card)')
    await expectVisible(page.getByPlaceholder('What strategic question should the pipeline analyze?'), 'Pipeline modal')
    await beat(page)
    const q2 = page.getByPlaceholder('What strategic question should the pipeline analyze?')
    await humanType(
      q2,
      'Should we expand Cardinal Element into a product + services hybrid model?',
      'pipeline question'
    )
    await dwell(page, HOLD_MS, 'before start pipeline')
    await safeClick(page.getByRole('button', { name: 'Start Pipeline' }), 'Start Pipeline')
    // Brief beat while status shows Running / progress.
    await dwell(page, BEAT_MS, 'pipeline running')

    pipelineEnd = await waitForRunEnd(page, 20 * 60_000)
    console.log(`[hosted-demo] pipeline ended: ${pipelineEnd}`)
    if (pipelineEnd === 'completed') {
      await dwell(page, HOLD_MS, 'pipeline completed — overview')
      try {
        await page.mouse.wheel(0, 320)
        await dwell(page, BEAT_MS, 'scroll outputs')
        await page.mouse.wheel(0, 480)
        await dwell(page, BEAT_MS, 'scroll synthesis / report')
      } catch {
        /* ignore scroll errors */
      }
      pipelinePdf = await downloadPdfIfPossible(page, 'pipeline')
      await dwell(page, Math.max(BEAT_MS, 3000), 'after Download PDF click')
      if (pipelinePdf) {
        await showPdfInRecording(page, pipelinePdf, 'pipeline')
      }
    } else {
      await dwell(page, ERROR_HOLD_MS, 'pipeline error on screen')
    }
    await dwell(page, HOLD_MS, 'end card')
  } catch (e) {
    console.error('[hosted-demo] step error (video still saved):', e)
  } finally {
    console.log('[hosted-demo] closing browser & flushing video')
    await context.close()
    await browser.close()
  }

  const dst = finalizeVideoFromTemp()
  if (!dst) {
    console.error('No recorded video found.')
    process.exit(1)
  }

  console.log('Demo artifacts written:')
  console.log(`- Video: ${dst}`)
  console.log(`- Protocol run: ${protocolEnd ?? 'n/a'}; PDF: ${protocolPdf ?? 'n/a'}`)
  console.log(`- Pipeline run: ${pipelineEnd ?? 'n/a'}; PDF: ${pipelinePdf ?? 'n/a'}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})

