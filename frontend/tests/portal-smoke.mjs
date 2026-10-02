// Run with Playwright available, or set PLAYWRIGHT_MODULE to its index.mjs file URL.
import { mkdir } from 'node:fs/promises'
import assert from 'node:assert/strict'
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const base = process.env.NERRO_TEST_URL || 'http://localhost:8080'
const output = process.env.NERRO_SCREENSHOTS || '../.local-tunnel/ui'
await mkdir(output, { recursive: true })
const failures = []
async function layout(page, name) {
  const dimensions = await page.evaluate(() => ({ width: innerWidth, content: document.documentElement.scrollWidth }))
  if (dimensions.content > dimensions.width + 2) failures.push(`${name}: horizontal overflow ${dimensions.content}/${dimensions.width}`)
}
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  page.on('pageerror', error => failures.push(error.message))
  await page.goto(base)
  await page.getByRole('heading', { name: 'Connecting places. Delivering possibilities.' }).waitFor()
  await layout(page, 'home desktop')
  await page.screenshot({ path: `${output}/home-desktop.png`, fullPage: true })
  assert.equal(await page.locator('.portal-service').count(), 4)
  await page.getByRole('button', { name: 'Use larger text size' }).click()
  assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize), '20px')
  await layout(page, 'home enlarged')
  await page.getByRole('button', { name: 'Use standard text size' }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(300)
  await layout(page, 'home mobile')
  await page.screenshot({ path: `${output}/home-mobile.png`, fullPage: true })
  await page.getByRole('button', { name: 'Workspace sign in' }).click()
  await page.getByLabel('Choose your demo workspace').waitFor()
  await layout(page, 'login mobile')
  await page.screenshot({ path: `${output}/login-mobile.png`, fullPage: true })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.getByRole('button', { name: 'Sign in securely' }).click()
  await page.locator('.sidebar').waitFor()
  const names = await page.locator('.sidebar .nav-item').allTextContents()
  for (const name of names) {
    await page.locator('.sidebar .nav-item').filter({ hasText: name.trim() }).click()
    await page.waitForTimeout(450)
    await layout(page, `admin ${name}`)
  }
  await page.locator('.sidebar .nav-item').filter({ hasText: 'Overview' }).click()
  await page.screenshot({ path: `${output}/workspace-desktop.png`, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(300)
  await layout(page, 'workspace mobile')
  await page.screenshot({ path: `${output}/workspace-mobile.png`, fullPage: true })
  await page.getByRole('button', { name: 'Toggle workspace navigation' }).click()
  await page.getByRole('button', { name: 'Sign out', exact: false }).click()
  await page.getByRole('heading', { name: 'Connecting places. Delivering possibilities.' }).waitFor()
  await context.close()
  // Read-only navigation checks for each remaining workspace; no reports or dispatches are created.
  for (const role of [1, 2, 3, 4, 5]) {
    const roleContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    const rolePage = await roleContext.newPage()
    rolePage.on('pageerror', error => failures.push(error.message))
    await rolePage.goto(base)
    await rolePage.getByRole('button', { name: 'Workspace sign in' }).click()
    await rolePage.getByLabel('Choose your demo workspace').selectOption(String(role))
    await rolePage.getByRole('button', { name: 'Sign in securely' }).click()
    await rolePage.locator('.sidebar').waitFor()
    const sections = await rolePage.locator('.sidebar .nav-item').allTextContents()
    for (const name of sections) {
      await rolePage.locator('.sidebar .nav-item').filter({ hasText: name.trim() }).click()
      await rolePage.waitForTimeout(350)
      await layout(rolePage, `role ${role} ${name}`)
    }
    await rolePage.setViewportSize({ width: 390, height: 844 })
    await layout(rolePage, `role ${role} mobile`)
    await roleContext.close()
  }
  console.log(JSON.stringify({ failures, screenshots: output }, null, 2))
  assert.deepEqual(failures, [])
} finally { await browser.close() }
