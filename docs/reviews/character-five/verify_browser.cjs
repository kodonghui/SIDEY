// Real Chromium interaction checks for the local candidate playground.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

(async () => {
  const output = process.env.SIDEY_REVIEW_OUTPUT || '/private/tmp/character-five-browser-evidence';
  fs.mkdirSync(output, { recursive: true });
  const sourceFiles = ['index.html', 'review.css', 'review.js', 'preview-state.js', 'review-audio.js', 'package.json', 'approvals.json', 'verify_browser.cjs'];
  const hashSources = () => Object.fromEntries(sourceFiles.map(file => [file,
    crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, file))).digest('hex')]));
  const source_sha256 = hashSources();
  const browser = await chromium.launch({ headless: true,
    ...(process.env.SIDEY_REVIEW_CHROMIUM ? { executablePath: process.env.SIDEY_REVIEW_CHROMIUM } : {}) });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [], checks = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => errors.push(request.url()));
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  // Observe real Web Audio starts as well as application status. No fake audio player.
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
  const canvas = id => page.locator(id).evaluate(node => node.toDataURL());
  const waitImpact = count => page.waitForFunction(n => window.sideyPreview.snapshot().impactCount === n, count);
  const waitIdleProjectile = () => page.waitForFunction(() => window.sideyPreview.snapshot().projectile === null);
  const ids = ['pixel_shiba', 'pixel_duck', 'pixel_poop', 'pixel_tteokbokki', 'pixel_quokka'];
  const items = ['tennis_ball', 'rubber_duck', 'tissue_ball', 'fish_cake_skewer', 'leaf'];
  try {
    await page.goto(process.env.SIDEY_REVIEW_URL || 'http://127.0.0.1:8765/');
    await page.waitForFunction(() => window.sideyPreview?.snapshot().ready);
    let before = await snapshot();
    assert.equal(before.actors.length, 5);
    assert.equal(before.playing, true);
    assert.equal(await audioCount(), 0);
    const firstCanvas = await canvas('#playground');
    await page.waitForTimeout(2200);
    let after = await snapshot();
    for (const actor of before.actors) {
      assert.notEqual(after.actors.find(next => next.id === actor.id).x, actor.x, `${actor.id} must actually walk`);
    }
    assert.notEqual(await canvas('#playground'), firstCanvas);
    assert.equal(await audioCount(), 0, 'walking must be silent before user input');
    checks.push('all five current candidates walk on load, including new quokka; actual canvas changes without autoplay audio');
    await page.screenshot({ path: path.join(output, 'playground.png') });

    // Test every sender and every signature object against a different moving actor.
    for (let i = 0; i < ids.length; i++) {
      await page.locator(`#sender-cards button[data-character="${ids[i]}"]`).click();
      assert.equal((await snapshot()).sender, ids[i]);
      assert.equal((await snapshot()).item, items[i]);
      await page.locator('#target').selectOption(ids[(i + 1) % ids.length]);
      await page.locator('#variant').selectOption(i % 2 ? 'B' : 'A');
      before = await snapshot();
      const starts = await audioCount();
      await page.locator('#throw').click();
      await page.waitForFunction(() => window.sideyPreview.snapshot().projectile !== null);
      const launched = await snapshot();
      assert.equal(launched.projectile.source, ids[i]);
      assert.equal(launched.projectile.target, ids[(i + 1) % ids.length]);
      assert.equal(await audioCount(), starts, 'no launch sound');
      await waitImpact(before.impactCount + 1);
      after = await snapshot();
      assert.equal(after.actors.find(actor => actor.id === ids[(i + 1) % ids.length]).motion, 'hit');
      assert.equal(await audioCount(), starts + 1, 'exactly one real sound start per collision');
      await waitIdleProjectile();
      await page.waitForTimeout(500);
      assert.notEqual((await snapshot()).actors.find(actor => actor.id === ids[i]).motion, 'throw');
    }
    checks.push('all five senders throw their selected item at moving targets; windup is silent; collision triggers hit and exactly one sound');

    for (const motion of ['idle', 'doze', 'offline', 'walk']) {
      await page.locator('#playground-motion').selectOption(motion);
      const actors = (await snapshot()).actors;
      assert.ok(actors.every(actor => actor.motion === motion));
    }
    await page.locator('#sound-toggle').uncheck();
    before = await snapshot();
    let silentStarts = await audioCount();
    await page.locator('#throw').click();
    await waitImpact(before.impactCount + 1);
    await waitIdleProjectile();
    assert.equal(await audioCount(), silentStarts, 'explicit mute still animates impact without audio');
    await page.locator('#sound-toggle').check();
    before = await snapshot();
    silentStarts = await audioCount();
    await page.locator('#throw').click();
    await page.waitForFunction(() => window.sideyPreview.snapshot().projectile?.phase === 'flight');
    await page.locator('#playground-play').click();
    await page.waitForTimeout(1200);
    assert.equal((await snapshot()).impactCount, before.impactCount);
    assert.equal(await audioCount(), silentStarts, 'pausing in flight cancels the pending impact sound');
    await page.locator('#playground-play').click();
    checks.push('idle/doze/sleep/walk work for all actors; mute preserves visual impact; pausing in flight prevents a ghost impact or sound');

    before = await snapshot();
    silentStarts = await audioCount();
    await page.locator('#throw').click();
    await page.waitForFunction(() => window.sideyPreview.snapshot().projectile?.phase === 'flight');
    const priorCanvasWidth = await page.locator('#playground').evaluate(node => node.width);
    await page.setViewportSize({ width: 900, height: 900 });
    await page.waitForFunction(width => document.querySelector('#playground').width !== width, priorCanvasWidth);
    await page.waitForFunction(() => window.sideyPreview.snapshot().projectile === null);
    assert.equal(await page.locator('#throw').isDisabled(), false);
    await page.waitForTimeout(1100);
    assert.equal((await snapshot()).impactCount, before.impactCount);
    assert.equal(await audioCount(), silentStarts);
    await page.locator('#throw').click();
    await waitImpact(before.impactCount + 1);
    await waitIdleProjectile();
    await page.setViewportSize({ width: 1280, height: 900 });
    checks.push('resizing during flight cancels the shot and sound without locking the throw button; retry succeeds');

    // Canvas pointer selection is scaled through its displayed bounds.
    await page.locator('#playground').scrollIntoViewIfNeeded();
    await page.waitForFunction(() => {
      const canvas = document.querySelector('#playground');
      return canvas.width === Math.floor(canvas.clientWidth);
    });
    after = await snapshot();
    const actor = after.actors.find(actor => actor.id !== after.sender);
    const geometry = await page.locator('#playground').evaluate(node => {
      const rect = node.getBoundingClientRect();
      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, logicalWidth: node.width, logicalHeight: node.height };
    });
    before = after;
    await page.mouse.click(geometry.x + actor.x * geometry.width / geometry.logicalWidth,
      geometry.y + actor.y * geometry.height / geometry.logicalHeight);
    await waitImpact(before.impactCount + 1);
    await waitIdleProjectile();
    checks.push('clicking a different canvas character throws at that target');

    await page.locator('#playground-play').click();
    before = await snapshot();
    const frozen = await canvas('#playground');
    await page.waitForTimeout(300);
    assert.equal(await canvas('#playground'), frozen);
    assert.equal((await snapshot()).playing, false);
    await page.locator('#playground-play').click();
    await page.waitForTimeout(300);
    assert.notEqual(await canvas('#playground'), frozen);
    checks.push('pause freezes the scene and resume restores motion');

    // Single, triple, A/B, existing-reference playback all use decoded WAV buffers.
    for (const [selector, expected] of [['#sound-once', 1], ['#sound-three', 3], ['#sound-ab', 2], ['#sound-reference', 1]]) {
      const starts = await audioCount();
      await page.locator(selector).click();
      await page.waitForFunction(n => window.__audioPlayed().length === n, starts + expected);
      await page.locator('#stop-audio').click();
      assert.equal((await snapshot()).audio.pending, 0);
      assert.equal((await snapshot()).audio.active, 0);
    }
    checks.push('single, three-repeat, A/B and existing-reference playback start real decoded buffers; explicit stop clears active and pending audio');

    for (let i = 0; i < ids.length; i++) {
      await page.locator('#sender').selectOption(ids[i]);
      const text = JSON.parse(fs.readFileSync(path.join(__dirname, 'copy-v1', `${ids[i]}.json`)));
      assert.ok((await page.locator('#selected-character-copy').textContent()).includes(text.character.description));
      assert.ok((await page.locator('#selected-item-copy').textContent()).includes(text.keepsake.description));
      for (const variant of ['A', 'B']) {
        await page.locator('#variant').selectOption(variant);
        const starts = await audioCount();
        await page.locator('#sound-once').click();
        await page.waitForFunction(n => window.__audioPlayed().length === n, starts + 1);
        await page.locator('#stop-audio').click();
      }
    }
    checks.push('all ten A/B candidates decode and start in Chromium; all ten character/item descriptions match the pinned files');

    let starts = await audioCount();
    await page.locator('#sound-three').click();
    await page.waitForFunction(n => window.__audioPlayed().length === n, starts + 1);
    await page.locator('#item').selectOption('tennis_ball');
    await page.waitForTimeout(1800);
    assert.equal(await audioCount(), starts + 1, 'selection change cancels queued sounds');
    starts = await audioCount();
    await page.locator('#sound-three').click();
    await page.waitForFunction(n => window.__audioPlayed().length === n, starts + 1);
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, value: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    before = await snapshot();
    assert.equal(before.playing, false);
    assert.equal(before.audio.active, 0);
    assert.equal(before.audio.pending, 0);
    await page.waitForTimeout(1800);
    assert.equal(await audioCount(), starts + 1, 'hidden document cannot play scheduled audio');
    await page.evaluate(() => { delete document.hidden; });
    checks.push('item changes and hidden-document events cancel queued and active audio; hidden scene pauses');

    // Old hash URLs must open the relevant details and show current assets.
    await page.evaluate(() => { location.hash = 'frames'; });
    await page.locator('.frame-button').first().waitFor({ state: 'visible' });
    assert.equal(await page.locator('.frame-button').count(), 90);
    assert.equal(await page.locator('.frame-button[data-source="candidate"]').count(), 90);
    await page.locator('.frame-button[data-character="pixel_quokka"]').nth(3).click();
    assert.equal(await page.locator('#character').inputValue(), 'pixel_quokka');
    await page.locator('#source').selectOption('original');
    assert.equal(await page.locator('.frame-button[data-source="original"]').count(), 90);
    const originalQuokka = await canvas('#stage');
    await page.locator('#source').selectOption('candidate');
    assert.notEqual(await canvas('#stage'), originalQuokka);
    for (const background of ['light', 'dark', 'checker']) {
      await page.locator('#background').selectOption(background);
      for (const edge of ['top', 'bottom', 'left', 'right']) {
        await page.locator('#edge').selectOption(edge);
        for (const scale of ['2', '4', '6']) await page.locator('#scale').selectOption(scale);
      }
    }
    await page.locator('#flip').check();
    await page.locator('#motion-select').selectOption('walk');
    await page.locator('#play').click();
    before = await snapshot();
    assert.equal(before.owner, 'inspector');
    await page.locator('#play').click();
    await page.evaluate(() => { location.hash = 'appearance'; });
    await page.locator('#appearance').screenshot({ path: path.join(output, 'appearance.png') });
    await page.evaluate(() => { location.hash = 'keepsakes'; });
    await page.locator('#keepsakes').screenshot({ path: path.join(output, 'keepsakes.png') });
    assert.equal(await page.locator('.keepsake-frame-button').count(), 60);
    checks.push('deep links open details; all 90 current frames including quokka; explicit original comparison; integer scales/backgrounds/edges/flip; 60 item frames');

    await page.locator('#reset').click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => { location.hash = ''; window.scrollTo(0, 0); });
    await page.screenshot({ path: path.join(output, 'mobile.png') });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    checks.push('390px viewport has no document overflow');

    const failurePage = await browser.newPage();
    await failurePage.route('**/candidates/character-v2/pixel_quokka/base.png*', route => route.fulfill({ status: 404, body: 'intentional missing-candidate test' }));
    await failurePage.goto(process.env.SIDEY_REVIEW_URL || 'http://127.0.0.1:8765/');
    await failurePage.waitForFunction(() => document.querySelector('#load-status').classList.contains('error'));
    assert.equal(await failurePage.locator('#throw').isDisabled(), true);
    assert.equal(await failurePage.evaluate(() => window.sideyPreview.snapshot().ready), false);
    assert.match(await failurePage.locator('#load-status').textContent(), /쿼카/);
    await failurePage.close();

    const racePage = await browser.newPage();
    await racePage.addInitScript(() => {
      const decode = AudioContext.prototype.decodeAudioData;
      AudioContext.prototype.decodeAudioData = async function (...args) {
        const result = await decode.apply(this, args);
        await new Promise(resolve => setTimeout(resolve, 300));
        return result;
      };
    });
    await racePage.goto(process.env.SIDEY_REVIEW_URL || 'http://127.0.0.1:8765/');
    await racePage.waitForFunction(() => window.sideyPreview?.snapshot().ready && !document.querySelector('#throw').disabled);
    await racePage.locator('#throw').click();
    await racePage.locator('#item').selectOption('leaf');
    await racePage.waitForTimeout(1000);
    const cancelled = await racePage.evaluate(() => window.sideyPreview.snapshot());
    assert.equal(cancelled.projectile, null);
    assert.equal(cancelled.impactCount, 0);
    assert.equal(cancelled.audio.started, 0);
    await racePage.locator('#throw').click();
    await racePage.waitForFunction(() => window.sideyPreview.snapshot().impactCount === 1);
    await racePage.close();
    checks.push('missing new quokka blocks playback without original fallback; selection during delayed audio decoding cancels the stale throw and the next explicit throw works');

    const interruptedPage = await browser.newPage();
    await interruptedPage.addInitScript(() => {
      const decode = AudioContext.prototype.decodeAudioData;
      let interruptOnce = true;
      AudioContext.prototype.decodeAudioData = async function (...args) {
        const result = await decode.apply(this, args);
        if (interruptOnce) { interruptOnce = false; await this.suspend(); }
        return result;
      };
    });
    await interruptedPage.goto(process.env.SIDEY_REVIEW_URL || 'http://127.0.0.1:8765/');
    await interruptedPage.waitForFunction(() => window.sideyPreview?.snapshot().ready && !document.querySelector('#throw').disabled);
    await interruptedPage.locator('#throw').click();
    await interruptedPage.waitForFunction(() => document.querySelector('#audio-status').textContent.includes('중단'));
    assert.equal(await interruptedPage.locator('#throw').isDisabled(), false);
    await interruptedPage.locator('#throw').click();
    await interruptedPage.waitForFunction(() => window.sideyPreview.snapshot().impactCount === 1);
    await interruptedPage.close();
    checks.push('audio context suspension during preparation reports an interruption and allows a successful retry');
    assert.deepEqual(errors, []);
    const startsDetail = await page.evaluate(() => window.__audioPlayed());
    assert.ok(startsDetail.every(item => item.length > 0 && item.rate > 0 && item.contextState === 'running'));
    assert.deepEqual(hashSources(), source_sha256, 'review source must not change during browser validation');
    const report = { browser: `Chromium ${browser.version()}`, surface: 'local headless Chromium; connected Browser plugin unavailable',
      checks, errors, actual_audio_starts: startsDetail.length, source_sha256,
      limitations: ['Audio decoded and real Web Audio starts observed; no physical speaker or human listening certification.',
        'Visibility tested with a simulated document.hidden event; no OS minimization or native app runtime verification.',
        'All art and audio remain review candidates; successful interaction tests do not record user approval.'] };
    fs.writeFileSync(path.join(output, 'browser-validation.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
