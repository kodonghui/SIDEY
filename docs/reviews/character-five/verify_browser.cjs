// Browser verification focuses on reviewing assets directly, not room controls.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
(async () => {
  const output = process.env.SIDEY_REVIEW_OUTPUT || '/private/tmp/character-five-browser-evidence';
  fs.mkdirSync(output, { recursive: true });
  const files = ['index.html', 'review.css', 'review.js', 'preview-state.js', 'review-audio.js', 'package.json', 'approvals.json', 'verify_browser.cjs'];
  const hashes = () => Object.fromEntries(files.map(file => [file, crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, file))).digest('hex')]));
  const source_sha256 = hashes();
  const browser = await chromium.launch({headless: true, ...(process.env.SIDEY_REVIEW_CHROMIUM ? {executablePath: process.env.SIDEY_REVIEW_CHROMIUM} : {})});
  const page = await browser.newPage({viewport: {width: 1280, height: 900}});
  const errors = [], checks = [], audioPaths = new Set();
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => errors.push(request.url()));
  page.on('response', response => { if (response.url().includes('/candidates/audio-')) audioPaths.add(new URL(response.url()).pathname); if(response.status() >= 400) errors.push(response.url()); });
  await page.addInitScript(() => {
    const observed = [];
    const byNode = new WeakMap();
    const start = AudioBufferSourceNode.prototype.start;
    const stop = AudioBufferSourceNode.prototype.stop;
    AudioBufferSourceNode.prototype.start = function (...args) {
      const result = start.apply(this, args);
      const context = this.context;
      const entry = { length: this.buffer?.length, rate: this.buffer?.sampleRate,
        contextState: context.state, when: args[0] ?? context.currentTime, cancelled: false, played: false,
        due() { return this.played || (!this.cancelled && context.currentTime >= this.when); } };
      observed.push(entry);
      byNode.set(this, entry);
      return result;
    };
    AudioBufferSourceNode.prototype.stop = function (...args) {
      const entry = byNode.get(this);
      if (entry) { entry.played = entry.due(); entry.cancelled = true; }
      return stop.apply(this, args);
    };
    window.__audioPlayed = () => observed.filter(entry => entry.due()).map(({ length, rate, contextState }) => ({ length, rate, contextState }));
  });
  const snapshot = () => page.evaluate(() => window.sideyPreview.snapshot());
  const audioCount = () => page.evaluate(() => window.__audioPlayed().length);
  try {
    await page.goto(process.env.SIDEY_REVIEW_URL || 'http://127.0.0.1:8765/');
    await page.waitForFunction(() => window.sideyPreview?.snapshot().ready);
    assert.equal(await page.locator('.character-review-card').count(), 5);
    assert.equal(await page.locator('.keepsake-review-card').count(), 5);
    assert.equal(await page.locator('#sender, #target, #interaction-count').count(), 0);
    assert.equal(await audioCount(), 0);
    const before = await snapshot();
    await page.waitForTimeout(1200);
    const after = await snapshot();
    for (const card of before.cards.filter(card => card.type === 'character')) {
      const next = after.cards.find(next => next.id === card.id);
      assert.equal(next.motion, 'walk');
      assert.notEqual(next.x, card.x, `${card.id} must walk`);
    }
    assert.ok(after.loadedCurrentPaths.some(file => file.includes('character-v3/pixel_quokka/base.png')));
    checks.push('five current characters walk in their cards; quokka uses scarf v3; no sender/target/collision-count interface or automatic sound');
    for (const card of await page.locator('.character-review-card').all()) {
      for (const motion of ['idle', 'doze', 'offline', 'throw', 'hit', 'walk']) {
        await card.locator('.character-motion').selectOption(motion);
      }
    }
    await page.screenshot({path: path.join(output, 'characters.png')});
    assert.equal(await page.locator('.sound-button').count(), 11);
    for (const item of ['tissue_ball', 'leaf']) {
      for (const variant of ['A', 'B']) assert.ok(audioPaths.has(`/candidates/audio-v3/${item}/${variant}.wav`));
      assert.ok(![...audioPaths].some(path => path.includes(`/audio-v1/${item}/`)));
    }
    for (const button of await page.locator('.sound-button').all()) {
      const starts = await audioCount();
      await button.click();
      await page.waitForFunction(count => window.__audioPlayed().length === count + 1, starts);
      assert.ok((await snapshot()).audio.active <= 1);
    }
    assert.ok((await snapshot()).playing, 'direct sound comparison must not stop silent walking');
    await page.locator('#stop-audio').click();
    assert.equal((await snapshot()).audio.active, 0);
    assert.equal((await snapshot()).audio.pending, 0);
    checks.push('all 11 direct sound buttons play real decoded audio without throwing or choosing characters; one active sound; silent animation continues');
    await page.locator('#keepsake-cards').screenshot({path: path.join(output, 'keepsakes.png')});
    for (const card of await page.locator('.keepsake-review-card').all()) {
      for (const view of ['impact', 'rotation', 'composite']) {
        await card.locator(`[data-view="${view}"]`).click();
        await page.waitForTimeout(view === 'composite' ? 1500 : 80);
      }
    }
    await page.locator('#stop-audio').click();
    const beforePause = await page.locator('.character-preview').first().evaluate(canvas => canvas.toDataURL());
    await page.locator('#pause-all').click();
    const paused = await page.locator('.character-preview').first().evaluate(canvas => canvas.toDataURL());
    await page.waitForTimeout(250);
    assert.equal(await page.locator('.character-preview').first().evaluate(canvas => canvas.toDataURL()), paused);
    await page.locator('#pause-all').click();
    await page.waitForTimeout(250);
    assert.notEqual(await page.locator('.character-preview').first().evaluate(canvas => canvas.toDataURL()), beforePause);
    checks.push('rotation, impact and fixed composite previews work per item; pause/resume freezes and restores motion');
    await page.locator('.sound-button').first().click();
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {configurable: true, value: true});
      document.dispatchEvent(new Event('visibilitychange'));
    });
    assert.equal((await snapshot()).audio.active, 0);
    assert.equal((await snapshot()).audio.pending, 0);
    assert.equal((await snapshot()).playing, false);
    await page.evaluate(() => { delete document.hidden; });
    await page.evaluate(() => { location.hash = 'frames'; });
    await page.locator('.frame-button').first().waitFor({state: 'visible'});
    assert.equal(await page.locator('.frame-button[data-source="candidate"]').count(), 90);
    await page.locator('.frame-button[data-character="pixel_quokka"]').first().click();
    const freshQuokka = await page.locator('#stage').evaluate(canvas => canvas.toDataURL());
    await page.locator('#source').selectOption('original');
    assert.notEqual(await page.locator('#stage').evaluate(canvas => canvas.toDataURL()), freshQuokka);
    await page.locator('#source').selectOption('candidate');
    for (const bg of ['light', 'dark', 'checker']) await page.locator('#background').selectOption(bg);
    for (const edge of ['bottom', 'top', 'left', 'right']) await page.locator('#edge').selectOption(edge);
    await page.locator('#flip').check();
    checks.push('hidden document stops playback; detailed 90-frame/original/background/edge/flip comparison remains available');
    await page.setViewportSize({width:390,height:844});
    await page.evaluate(() => { location.hash = ''; window.scrollTo(0,0); });
    await page.screenshot({path:path.join(output,'mobile.png')});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    checks.push('390px viewport has no document overflow');
    assert.deepEqual(errors, []);
    assert.deepEqual(hashes(), source_sha256, 'source must remain unchanged during validation');
    const report = {browser:`Chromium ${browser.version()}`, surface:'local headless Chromium; connected Browser plugin unavailable',checks, errors, source_sha256,
      actual_audio_starts: await audioCount(), limitations:['Real Web Audio starts and decoding verified, not physical speaker quality or user listening approval.','Visibility uses a simulated document.hidden event; no native app execution.']};
    fs.writeFileSync(path.join(output,'browser-validation.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
