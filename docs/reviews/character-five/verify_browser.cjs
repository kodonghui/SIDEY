// Run with NODE_PATH pointing to an installed Playwright package. Screenshots
// stay outside the package: generated evidence is not an approved art asset.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

(async () => {
  const output = process.env.SIDEY_REVIEW_OUTPUT || '/private/tmp/character-five-browser-evidence';
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    ...(process.env.SIDEY_REVIEW_CHROMIUM ? { executablePath: process.env.SIDEY_REVIEW_CHROMIUM } : {}) });
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => errors.push(request.url()));
  const checks = [];
  try {
    await page.goto(process.env.SIDEY_REVIEW_URL || 'http://127.0.0.1:8765/');
    await page.waitForFunction(() => document.querySelectorAll('.frame-button').length === 90);
    assert.match(await page.locator('#load-status').textContent(), /90프레임/);
    assert.equal(await page.locator('.appearance-card').count(), 5);
    checks.push('10 original sheets loaded; 90 frame buttons; 5 appearance comparisons');
    for (const index of [0, 17, 35, 53, 71, 89]) {
      const button = page.locator('.frame-button').nth(index);
      await button.click();
      assert.equal(await button.getAttribute('aria-pressed'), 'true');
      assert.equal(await page.locator('#play').textContent(), '재생');
    }
    checks.push('manual frame selection across all five characters pauses playback');
    const snapshot = () => page.locator('#stage').evaluate(canvas => canvas.toDataURL());
    await page.locator('#character').selectOption('pixel_shiba');
    const original = await snapshot();
    await page.locator('#flip').check();
    assert.notEqual(await snapshot(), original);
    await page.locator('#flip').uncheck();
    await page.locator('#silhouette').check();
    assert.notEqual(await snapshot(), original);
    await page.locator('#silhouette').uncheck();
    checks.push('flip and silhouette change the rendered canvas');
    for (const background of ['light', 'dark', 'checker']) {
      await page.locator('#background').selectOption(background);
      for (const edge of ['bottom', 'top', 'left', 'right']) {
        await page.locator('#edge').selectOption(edge);
        for (const scale of ['2', '4', '6', '8']) {
          await page.locator('#scale').selectOption(scale);
          assert.match(await page.locator('#stage').getAttribute('aria-label'), new RegExp(`${scale}배`));
        }
      }
    }
    checks.push('3 backgrounds × 4 edges × 4 integer scales render successfully');
    await page.locator('#scale').selectOption('4');
    await page.locator('#edge').selectOption('bottom');
    await page.locator('#motion-select').selectOption('walk');
    const stopped = await snapshot();
    await page.locator('#play').click();
    await page.waitForTimeout(210);
    assert.notEqual(await snapshot(), stopped);
    await page.locator('#play').click();
    const paused = await snapshot();
    await page.waitForTimeout(210);
    assert.equal(await snapshot(), paused);
    checks.push('walk advances pixels; pause freezes canvas');
    for (const motion of ['throw', 'hit']) {
      await page.locator('#motion-select').selectOption(motion);
      await page.locator('#play').click();
      await page.waitForFunction(() => document.querySelector('#motion-select').value === 'idle');
      assert.equal(await page.locator('#frame').inputValue(), '0');
      assert.equal(await page.locator('#play').textContent(), '재생');
    }
    checks.push('throw and hit play once and return to idle 0');
    await page.locator('#timing').selectOption('proposal');
    await page.locator('#frame').selectOption('1');
    await page.locator('#play').click();
    await page.waitForTimeout(380);
    assert.equal(await page.locator('#frame').inputValue(), '0');
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, value: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    assert.equal(await page.locator('#play').textContent(), '재생');
    checks.push('proposed idle closed-eye duration; simulated hidden-document event pauses');
    await page.evaluate(() => { delete document.hidden; });
    await page.locator('#timing').selectOption('current');
    await page.locator('#appearance').screenshot({ path: path.join(output, 'appearance.png') });
    await page.locator('#keepsakes').screenshot({ path: path.join(output, 'keepsakes.png') });
    await page.locator('#motion').screenshot({ path: path.join(output, 'motion.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    assert.equal(overflow, false, 'page must not overflow; stage has its own scroll container');
    checks.push('390px layout has no document overflow');
    assert.deepEqual(errors, []);
    const hashes = {};
    for (const file of ['index.html', 'review.css', 'review.js', 'package.json', 'approvals.json']) {
      hashes[file] = crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, file))).digest('hex');
    }
    const report = { browser: `Chromium ${browser.version()}`, surface: 'isolated local headless browser; connected Browser plugin unavailable',
      checks, errors, source_sha256: hashes,
      limitations: ['Visibility handler tested by a simulated document.hidden event, not OS tab minimization.',
        'Current original motion preview only; no final animation/audio approval or app runtime verification.'] };
    fs.writeFileSync(path.join(output, 'browser-validation.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
