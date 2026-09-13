import { CHARACTERS, ITEMS, MOTIONS, TIMING, frameAt, advanceWalk, flightDuration, projectilePoint } from './preview-state.js?v=playground-v3';
import { createReviewAudio } from './review-audio.js?v=playground-v3';

const $ = id => document.getElementById(id);
const url = path => `${path}?v=playground-v3`;
const sheets = new Map();
const objects = new Map();
const copy = new Map();
const spriteCache = new Map();
const state = { ready: false, owner: 'paused', playing: false, time: 0, epoch: 0,
  sender: CHARACTERS[0].id, target: CHARACTERS[1].id, item: CHARACTERS[0].item,
  variant: 'A', soundEnabled: true, preparingThrow: false, motion: 'walk', actors: [], projectile: null,
  impactCount: 0, errors: [] };
const inspector = { character: CHARACTERS[0].id, source: 'candidate', motion: 'walk', frame: 2,
  scale: 4, background: 'checker', edge: 'bottom', timing: 'current', flip: false,
  silhouette: false, baseline: true, elapsed: 0 };
let request = null;
let lastTick = null;
let lastPaint = null;
const audio = createReviewAudio(message => { $('audio-status').textContent = message; $('audio-status').classList.add('error'); });

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function image(path, width, height) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => img.naturalWidth === width && img.naturalHeight === height
      ? resolve(img) : reject(new Error(`${path}: ${width}×${height} 규격이 아닙니다.`));
    img.onerror = () => reject(new Error(`${path}: 이미지 파일을 불러오지 못했습니다.`));
    img.src = url(path);
  });
}
function sprite(img, frame, cell = 24, scale = 2, silhouette = false) {
  const key = `${img.src}:${frame}:${cell}:${scale}:${silhouette}`;
  if (spriteCache.has(key)) return spriteCache.get(key);
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = cell * scale;
  const context = canvas.getContext('2d');
  context.imageSmoothingEnabled = false;
  context.drawImage(img, frame * cell, 0, cell, cell, 0, 0, canvas.width, canvas.height);
  if (silhouette) {
    context.globalCompositeOperation = 'source-in'; context.fillStyle = '#213b2b';
    context.fillRect(0, 0, canvas.width, canvas.height);
  }
  spriteCache.set(key, canvas);
  return canvas;
}
function spriteCopy(img, frame, cell = 24, scale = 3, silhouette = false, baseline = false) {
  const source = sprite(img, frame, cell, scale, silhouette);
  const canvas = document.createElement('canvas'); canvas.width = source.width; canvas.height = source.height;
  const context = canvas.getContext('2d'); context.drawImage(source, 0, 0);
  if (baseline) { context.fillStyle = '#3284b9'; context.fillRect(0, 21 * scale, canvas.width, 1); }
  return canvas;
}
function backdrop(context, width, height, name) {
  context.fillStyle = name === 'dark' ? '#253329' : '#fafaf3'; context.fillRect(0, 0, width, height);
  if (name === 'checker') {
    context.fillStyle = '#e6ecdd';
    for (let y = 0; y < height; y += 16) for (let x = 0; x < width; x += 16) {
      if ((x / 16 + y / 16) % 2 === 0) context.fillRect(x, y, 16, 16);
    }
  }
}
function stopWork(owner = 'paused') {
  state.epoch += 1;
  if (request !== null) cancelAnimationFrame(request);
  request = null; lastTick = lastPaint = null;
  audio.stop(); state.playing = false; state.owner = owner; state.projectile = null; state.preparingThrow = false;
  for (const actor of state.actors) actor.action = null;
  updatePlaybackUI();
}
function start(owner) {
  if (!state.ready || document.hidden) return;
  state.owner = owner; state.playing = true; lastTick = lastPaint = null;
  if (request !== null) cancelAnimationFrame(request);
  request = requestAnimationFrame(tick); updatePlaybackUI();
}
function updatePlaybackUI() {
  $('playground-play').textContent = state.playing && state.owner === 'playground' ? '일시정지' : '다시 걷기';
  $('play').textContent = state.playing && state.owner === 'inspector' ? '일시정지' : '재생';
  $('throw').disabled = !state.ready || state.preparingThrow || !!state.projectile || state.sender === state.target || (state.soundEnabled && !audio.has(currentAudioKey()));
  $('playground-status').textContent = !state.ready ? '최신 후보를 불러오는 중' : state.playing && state.owner === 'playground'
    ? `${MOTIONS[state.motion].name} · 다른 친구를 누르면 던져요` : '잠시 멈춤 · 다시 걷기를 눌러 주세요';
}
function resetActors() {
  const width = $('playground').width;
  state.actors = CHARACTERS.map((character, i) => ({ id: character.id,
    x: 30 + (width - 60) * (i + 0.5) / CHARACTERS.length,
    y: 214, direction: i % 2 ? -1 : 1, motion: state.motion, frame: frameAt(state.motion, 0),
    sheet: 'base', action: null }));
}
function resizePlayground() {
  const canvas = $('playground'); const width = Math.max(240, Math.floor(canvas.clientWidth));
  if (canvas.width !== width) {
    const ratio = width / canvas.width; canvas.width = width;
    for (const actor of state.actors) actor.x *= ratio;
    if (state.projectile || state.preparingThrow) {
      const resume = state.playing && state.owner === 'playground';
      stopWork('playground'); updateActors(0);
      if (resume) start('playground');
    }
    updatePlaybackUI();
  }
  drawPlayground();
}
function updateActors(dt) {
  for (const actor of state.actors) {
    if (actor.action && state.time - actor.action.at >= (actor.action.motion === 'hit' ? TIMING.hit : TIMING.throwing)) actor.action = null;
    actor.motion = actor.action?.motion ?? state.motion;
    const elapsed = actor.action ? state.time - actor.action.at : state.time;
    if (actor.motion === 'walk') Object.assign(actor, advanceWalk(actor, dt, $('playground').width, 2));
    actor.frame = frameAt(actor.motion, elapsed); actor.sheet = MOTIONS[actor.motion].sheet;
  }
}
function actorPoint(id) {
  const actor = state.actors.find(item => item.id === id);
  return { x: actor.x, y: actor.y - 5 };
}
function updateProjectile() {
  const shot = state.projectile;
  if (!shot) return;
  if (shot.phase === 'windup' && state.time - shot.at >= TIMING.release) {
    shot.phase = 'flight'; shot.start = actorPoint(shot.source); shot.releasedAt = shot.at + TIMING.release;
    shot.duration = flightDuration(Math.abs(actorPoint(shot.target).x - shot.start.x));
  }
  if (shot.phase === 'flight') {
    const elapsed = state.time - shot.releasedAt;
    Object.assign(shot, projectilePoint(shot.start, actorPoint(shot.target), elapsed / shot.duration));
    if (elapsed >= shot.duration) {
      shot.phase = 'impact'; shot.impactAt = state.time;
      const target = state.actors.find(actor => actor.id === shot.target);
      target.action = { motion: 'hit', at: state.time }; target.motion = 'hit'; target.sheet = 'throw_hit'; target.frame = 4;
      state.impactCount += 1;
      $('interaction-count').textContent = `충돌 ${state.impactCount}회`;
      if (state.soundEnabled) {
        if (!audio.playPrepared(`${shot.item}/${shot.variant}`)) $('audio-status').textContent = '충돌음이 준비되지 않았습니다. 소리 켜기를 다시 눌러 주세요.';
      }
    }
  }
  if (shot.phase === 'impact' && state.time - shot.impactAt >= TIMING.impact) state.projectile = null;
  updatePlaybackUI();
}
function drawPlayground() {
  const canvas = $('playground'); const context = canvas.getContext('2d');
  context.fillStyle = '#eef1e4'; context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#d4dfc4'; context.fillRect(0, 232, canvas.width, 2);
  context.fillStyle = '#e3ead7'; context.fillRect(0, 234, canvas.width, 66);
  context.imageSmoothingEnabled = false;
  for (const actor of state.actors) {
    const entry = sheets.get(actor.id)?.candidate; if (!entry) continue;
    const x = Math.round(actor.x); const y = Math.round(actor.y);
    context.save(); context.translate(x, y);
    if (actor.id === state.sender) {
      context.strokeStyle = '#6c8c51'; context.lineWidth = 2; context.strokeRect(-27, -27, 54, 54);
    }
    // Manual inspector flip is separate; the playground faces the direction of travel/throw.
    context.scale(actor.direction < 0 ? -1 : 1, 1);
    context.drawImage(sprite(entry[actor.sheet], actor.frame), -24, -24); context.restore();
    context.textAlign = 'center'; context.font = '11px -apple-system, sans-serif'; context.fillStyle = '#66745a';
    context.fillText(CHARACTERS.find(item => item.id === actor.id).name, x, y + 42);
  }
  const shot = state.projectile;
  if (shot && shot.phase !== 'windup') {
    const frame = shot.phase === 'flight' ? Math.floor((state.time - shot.releasedAt) / TIMING.rotation) % 8
      : 8 + Math.min(3, Math.floor((state.time - shot.impactAt) / (TIMING.impact / 4)));
    const size = shot.phase === 'impact' ? 3 : 2;
    const bitmap = sprite(objects.get(shot.item), frame, 16, size);
    context.drawImage(bitmap, Math.round(shot.x - bitmap.width / 2), Math.round(shot.y - bitmap.height / 2));
  }
  canvas.dataset.phase = shot?.phase ?? 'none'; canvas.dataset.impacts = String(state.impactCount);
}
function tick(now) {
  if (!state.playing) return;
  const dt = lastTick === null ? 0 : Math.min(0.1, (now - lastTick) / 1000); lastTick = now;
  if (state.owner === 'playground') { state.time += dt; updateActors(dt); updateProjectile(); }
  else if (state.owner === 'inspector') inspector.elapsed += dt;
  if (lastPaint === null || now - lastPaint >= 1000 / 30 - 0.5) {
    lastPaint = now;
    if (state.owner === 'playground') drawPlayground();
    else if (state.owner === 'inspector') {
      const motion = MOTIONS[inspector.motion];
      if (['throw', 'hit'].includes(inspector.motion) && inspector.elapsed >= motion.frames.length * motion.step) {
        stopWork('inspector'); inspector.motion = 'idle'; inspector.frame = 0; inspector.elapsed = 0;
        $('motion-select').value = 'idle'; updateInspectorFrames();
      } else inspector.frame = frameAt(inspector.motion, inspector.elapsed, inspector.timing);
      drawInspector();
    }
  }
  if (state.playing) request = requestAnimationFrame(tick);
}
async function throwAt(target) {
  if (!state.ready || state.projectile || state.preparingThrow || target === state.sender) return;
  stopWork('playground'); state.target = target; $('target').value = target;
  const epoch = state.epoch;
  if (state.soundEnabled) {
    state.preparingThrow = true; updatePlaybackUI();
    try {
      const unlocked = await audio.unlock([currentAudioKey()]);
      if (epoch !== state.epoch) return;
      if (!unlocked) {
        state.preparingThrow = false; updatePlaybackUI();
        $('audio-status').textContent = '소리 준비가 중단됐습니다. 던지기를 다시 눌러 주세요.';
        $('audio-status').classList.add('error');
        return;
      }
    } catch (error) {
      if (epoch === state.epoch) {
        state.preparingThrow = false; updatePlaybackUI();
        $('audio-status').textContent = `충돌음 준비 오류: ${error.message} 소리를 끄면 무음으로 던질 수 있습니다.`;
        $('audio-status').classList.add('error');
      }
      return;
    }
  }
  if (epoch !== state.epoch) return;
  state.preparingThrow = false;
  const sender = state.actors.find(actor => actor.id === state.sender);
  sender.direction = actorPoint(target).x < sender.x ? -1 : 1;
  sender.action = { motion: 'throw', at: state.time };
  sender.motion = 'throw'; sender.frame = 0; sender.sheet = 'throw_hit';
  state.projectile = { phase: 'windup', source: state.sender, target, item: state.item,
    variant: state.variant, at: state.time, x: sender.x, y: sender.y };
  start('playground'); drawPlayground();
}
function currentAudioKey() { return `${state.item}/${state.variant}`; }
function updateAudioControls() {
  const available = state.ready && audio.has(currentAudioKey());
  $('sound-toggle').disabled = !state.ready;
  $('variant').disabled = !state.ready;
  $('sound-once').disabled = $('sound-three').disabled = !available;
  $('sound-ab').disabled = !state.ready || !audio.has(`${state.item}/A`) || !audio.has(`${state.item}/B`);
  $('sound-reference').disabled = !state.ready || !audio.has('reference');
  $('stop-audio').disabled = !state.ready;
  updatePlaybackUI();
}
function updateSoundPreference() {
  $('sound-toggle').checked = state.soundEnabled;
  $('audio-status').classList.remove('error');
  $('audio-status').textContent = state.soundEnabled ? '던질 때 충돌 소리 · 자동 산책은 무음' : '충돌 소리 꺼짐';
  updateAudioControls();
}
function selectionChanged(fn) {
  const resume = state.playing && state.owner === 'playground';
  stopWork('playground'); fn(); updateSoundPreference(); renderSelection(); drawPlayground();
  if (resume) start('playground');
}
function selectSender(id) {
  selectionChanged(() => {
    state.sender = id; state.item = CHARACTERS.find(item => item.id === id).item;
    if (state.target === id) state.target = CHARACTERS.find(item => item.id !== id).id;
  });
}
function renderSelection() {
  $('sender').value = state.sender; $('target').value = state.target; $('item').value = state.item;
  for (const option of $('target').options) option.disabled = option.value === state.sender;
  document.querySelectorAll('.character-card').forEach(card => card.setAttribute('aria-pressed', String(card.dataset.character === state.sender)));
  const selected = copy.get(state.sender);
  const itemCopy = [...copy.values()].find(entry => entry.keepsake.id === state.item);
  $('selected-character-copy').textContent = selected ? `${selected.character.name} · ${selected.character.description}` : '캐릭터 설명을 준비하는 중입니다.';
  $('selected-item-copy').textContent = itemCopy ? `${itemCopy.keepsake.name} · ${itemCopy.keepsake.description}` : '물건 설명을 준비하는 중입니다.';
  updateAudioControls(); updatePlaybackUI();
}
function enableSound() {
  const resume = state.playing && state.owner === 'playground';
  stopWork('playground'); state.soundEnabled = $('sound-toggle').checked;
  updateSoundPreference();
  if (resume) start('playground');
}
async function compareSound(keys, label) {
  stopWork('audio');
  const epoch = state.epoch; $('audio-status').textContent = `${label} · 소리 비교 중에는 놀이터가 멈춥니다.`;
  const played = await audio.compare(keys);
  if (epoch !== state.epoch) return;
  if (!played) $('audio-status').classList.add('error');
}
function drawInspector() {
  const canvas = $('stage'); const context = canvas.getContext('2d');
  backdrop(context, canvas.width, canvas.height, inspector.background);
  const spec = MOTIONS[inspector.motion]; const image = sheets.get(inspector.character)?.[inspector.source]?.[spec.sheet];
  if (!image) {
    $('frame-status').value = '선택한 자료를 불러오지 못했습니다. 원본으로 자동 대체하지 않습니다.';
    return;
  }
  const bitmap = sprite(image, inspector.frame, 24, inspector.scale, inspector.silhouette);
  const size = bitmap.width; const vertical = ['left', 'right'].includes(inspector.edge);
  const length = (vertical ? canvas.height : canvas.width) - size - 24;
  const phase = (length / 2 + (inspector.motion === 'walk' ? inspector.elapsed * 22 * inspector.scale / 2 : 0)) % (length * 2);
  const tangent = 12 + size / 2 + (phase <= length ? phase : length * 2 - phase);
  let x = tangent, y = canvas.height - size / 2 - 12, angle = 0;
  if (inspector.edge === 'top') { y = size / 2 + 12; angle = Math.PI; }
  if (inspector.edge === 'left') { x = size / 2 + 12; y = tangent; angle = Math.PI / 2; }
  if (inspector.edge === 'right') { x = canvas.width - size / 2 - 12; y = tangent; angle = -Math.PI / 2; }
  context.save(); context.imageSmoothingEnabled = false; context.translate(Math.round(x), Math.round(y)); context.rotate(angle);
  context.scale(inspector.flip ? -1 : 1, 1); context.drawImage(bitmap, -size / 2, -size / 2);
  if (inspector.baseline) { context.fillStyle = '#3689c2'; context.fillRect(-size / 2, 9 * inspector.scale, size, 1); }
  context.restore();
  $('frame').value = String(inspector.frame);
  const label = `${inspector.source === 'candidate' ? '최신 후보' : '수정 전 원본'} / ${inspector.character} / ${spec.sheet} ${inspector.frame} / ${inspector.scale}배`;
  $('frame-status').value = label; canvas.setAttribute('aria-label', label);
  document.querySelectorAll('.frame-button[aria-pressed="true"]').forEach(button => button.setAttribute('aria-pressed', 'false'));
  document.querySelector(`.frame-button[data-character="${inspector.character}"][data-sheet="${spec.sheet}"][data-frame="${inspector.frame}"]`)?.setAttribute('aria-pressed', 'true');
}
function updateInspectorFrames() {
  $('frame').replaceChildren(...MOTIONS[inspector.motion].frames.map(frame => new Option(String(frame), String(frame))));
  $('frame').value = String(inspector.frame);
}
function resetInspector(preserveFrame = false) {
  stopWork('inspector'); inspector.elapsed = 0;
  if (!preserveFrame) inspector.frame = MOTIONS[inspector.motion].frames[0];
  updateInspectorFrames(); drawInspector();
}
function motionFor(sheet, index) {
  return Object.keys(MOTIONS).find(key => MOTIONS[key].sheet === sheet && MOTIONS[key].frames.includes(index));
}
function renderCharacterGrids() {
  $('frame-list').replaceChildren(); let count = 0;
  for (const character of CHARACTERS) {
    const entry = sheets.get(character.id)?.[inspector.source];
    if (!entry) continue;
    const group = element('article', null, 'frame-group'); group.append(element('h3', character.name));
    for (const sheet of ['base', 'throw_hit']) {
      group.append(element('p', sheet === 'base' ? '기본 0–9' : '던지기·피격 0–7', 'frame-sheet-label'));
      const grid = element('div', null, 'frame-grid');
      for (let index = 0; index < (sheet === 'base' ? 10 : 8); index++) {
        const motion = motionFor(sheet, index); const button = element('button', null, 'frame-button'); button.type = 'button';
        Object.assign(button.dataset, { character: character.id, sheet, frame: String(index), source: inspector.source });
        button.setAttribute('aria-pressed', 'false'); button.setAttribute('aria-label', `${character.name} ${sheet} ${index}번 ${MOTIONS[motion].name}`);
        button.append(spriteCopy(entry[sheet], index, 24, 4, false, true), element('span', `${index} · ${motion}`));
        button.addEventListener('click', () => {
          inspector.character = character.id; inspector.motion = motion; inspector.frame = index;
          $('character').value = character.id; $('motion-select').value = motion;
          resetInspector(true); $('motion').scrollIntoView({ block: 'start' });
        }); grid.append(button); count += 1;
      }
      group.append(grid);
    }
    $('frame-list').append(group);
  }
  $('grid-status').textContent = `${inspector.source === 'candidate' ? '최신 후보' : '수정 전 원본'} ${count}프레임 · 모든 번호는 각 시트의 0부터 셉니다.`;
}
function renderAppearances() {
  $('appearance-list').replaceChildren();
  for (const character of CHARACTERS) {
    const entry = sheets.get(character.id); if (!entry?.candidate) continue;
    const card = element('article', null, 'appearance-card');
    card.append(element('h3', `${character.name} · ${character.id === 'pixel_quokka' ? '새 외형 검토 중' : '원본 외형 유지'}`));
    const grid = element('div', null, 'comparison');
    for (const [source, silhouette, label] of [['original', false, '원본'], ['candidate', false, '최신 후보'], ['original', true, '원본 실루엣'], ['candidate', true, '후보 실루엣']]) {
      const figure = element('figure');
      if (entry[source]) figure.append(spriteCopy(entry[source].base, 0, 24, 6, silhouette));
      else figure.append(element('p', '자료 없음'));
      figure.append(element('figcaption', label)); grid.append(figure);
    }
    card.append(grid); $('appearance-list').append(card);
  }
}
function renderItemGrids() {
  $('keepsake-frames').replaceChildren();
  for (const item of ITEMS) {
    const image = objects.get(item.id); if (!image) continue;
    const group = element('article', null, 'frame-group'); group.append(element('h3', item.name));
    const grid = element('div', null, 'keepsake-frame-grid');
    for (let frame = 0; frame < 12; frame++) {
      const button = element('button', null, 'keepsake-frame-button'); button.type = 'button';
      Object.assign(button.dataset, { object: item.id, frame: String(frame) }); button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', `${item.name} ${frame < 8 ? '회전' : '충돌'} ${frame}번`);
      button.append(spriteCopy(image, frame, 16, 4), element('span', `${frame} · ${frame < 8 ? '회전' : '충돌'}`));
      button.addEventListener('click', () => {
        stopWork('inspector'); const canvas = $('keepsake-stage'); const context = canvas.getContext('2d');
        backdrop(context, 160, 160, 'checker'); context.drawImage(sprite(image, frame, 16, 8), 16, 16);
        $('keepsake-frame-status').value = `${item.name} · ${frame < 8 ? '회전' : '충돌'} ${frame}번`;
        document.querySelectorAll('.keepsake-frame-button[aria-pressed="true"]').forEach(node => node.setAttribute('aria-pressed', 'false'));
        button.setAttribute('aria-pressed', 'true');
        canvas.scrollIntoView({ block: 'center' });
      }); grid.append(button);
    }
    group.append(grid); $('keepsake-frames').append(group);
  }
  const first = objects.get(ITEMS[0].id);
  if (first) {
    const context = $('keepsake-stage').getContext('2d'); backdrop(context, 160, 160, 'checker'); context.drawImage(sprite(first, 0, 16, 8), 16, 16);
    $('keepsake-frame-status').value = '테니스공 · 회전 0번';
  }
}
async function loadCopy() {
  const failures = [];
  await Promise.all(CHARACTERS.map(async character => {
    try {
      const response = await fetch(url(`copy-v1/${character.id}.json`), { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const entry = await response.json();
      if (entry.character_id !== character.id || typeof entry.character?.description !== 'string' || typeof entry.keepsake?.description !== 'string') throw new Error('설명 형식 오류');
      copy.set(character.id, entry);
    } catch (error) { failures.push(`${character.name} 설명: ${error.message}`); }
  }));
  for (const character of CHARACTERS) {
    const entry = copy.get(character.id); if (!entry) continue;
    const card = element('article', null, 'copy-card');
    card.append(element('h3', `${entry.character.name} · ${entry.keepsake.name}`), element('p', entry.character.description), element('p', entry.keepsake.description, 'item-description'));
    $('copy-list').append(card);
  }
  if (failures.length) $('copy-load-status').textContent = failures.join(' / ');
  renderSelection();
}
function openHash() {
  const id = location.hash.slice(1);
  if (['appearance', 'motion', 'frames', 'keepsakes', 'copy'].includes(id)) {
    $('review-details').open = true;
    stopWork('inspector');
    requestAnimationFrame(() => $(id).scrollIntoView({ block: 'start' }));
  }
}
function bind() {
  for (const id of ['sender', 'target', 'character']) $(id).append(...CHARACTERS.map(item => new Option(item.name, item.id)));
  $('target').value = state.target;
  $('item').append(...ITEMS.map(item => new Option(item.name, item.id)));
  $('motion-select').append(...Object.entries(MOTIONS).map(([key, spec]) => new Option(spec.name, key)));
  $('sender').addEventListener('change', event => selectSender(event.target.value));
  $('target').addEventListener('change', event => selectionChanged(() => { state.target = event.target.value; }));
  $('item').addEventListener('change', event => selectionChanged(() => { state.item = event.target.value; }));
  $('variant').addEventListener('change', event => selectionChanged(() => { state.variant = event.target.value; }));
  $('playground-motion').addEventListener('change', event => {
    stopWork('playground'); state.motion = event.target.value; updateActors(0); start('playground'); drawPlayground();
  });
  $('throw').addEventListener('click', () => throwAt(state.target));
  $('playground').addEventListener('click', event => {
    const rect = $('playground').getBoundingClientRect();
    const x = (event.clientX - rect.left) * $('playground').width / rect.width;
    const y = (event.clientY - rect.top) * $('playground').height / rect.height;
    const target = state.actors.filter(actor => actor.id !== state.sender && Math.abs(actor.x - x) <= 30 && Math.abs(actor.y - y) <= 30)
      .sort((a, b) => Math.hypot(a.x - x, a.y - y) - Math.hypot(b.x - x, b.y - y))[0];
    if (target) throwAt(target.id);
  });
  $('playground-play').addEventListener('click', () => {
    const wasPlaying = state.playing && state.owner === 'playground'; stopWork('playground');
    if (!wasPlaying) start('playground'); drawPlayground();
  });
  $('reset').addEventListener('click', () => {
    stopWork('playground'); state.time = 0; state.impactCount = 0; state.motion = 'walk';
    $('playground-motion').value = 'walk'; $('interaction-count').textContent = '충돌 0회';
    resetActors(); start('playground'); drawPlayground();
  });
  $('sound-toggle').addEventListener('change', enableSound);
  $('sound-once').addEventListener('click', () => compareSound([currentAudioKey()], `후보 ${state.variant}`));
  $('sound-three').addEventListener('click', () => compareSound(Array(3).fill(currentAudioKey()), `후보 ${state.variant} 3회 반복`));
  $('sound-ab').addEventListener('click', () => compareSound([`${state.item}/A`, `${state.item}/B`], 'A 다음 B'));
  $('sound-reference').addEventListener('click', () => compareSound(['reference'], '기존 야구공'));
  $('stop-audio').addEventListener('click', () => { stopWork(); $('audio-status').textContent = '모든 재생을 멈췄습니다.'; drawPlayground(); });
  $('character').addEventListener('change', event => { inspector.character = event.target.value; resetInspector(); });
  $('source').addEventListener('change', event => { inspector.source = event.target.value; renderCharacterGrids(); resetInspector(true); });
  $('motion-select').addEventListener('change', event => { inspector.motion = event.target.value; resetInspector(); });
  for (const key of ['scale', 'background', 'edge', 'timing']) $(key).addEventListener('change', event => {
    inspector[key] = key === 'scale' ? Number(event.target.value) : event.target.value; resetInspector(true);
  });
  for (const key of ['flip', 'silhouette', 'baseline']) $(key).addEventListener('change', event => { inspector[key] = event.target.checked; resetInspector(true); });
  $('frame').addEventListener('change', event => { inspector.frame = Number(event.target.value); resetInspector(true); });
  $('play').addEventListener('click', () => {
    const wasPlaying = state.playing && state.owner === 'inspector'; stopWork('inspector');
    if (!wasPlaying) {
      inspector.elapsed = inspector.motion === 'idle' && inspector.timing === 'proposal' ? (inspector.frame === 1 ? 2.4 : 0)
        : MOTIONS[inspector.motion].frames.indexOf(inspector.frame) * MOTIONS[inspector.motion].step;
      start('inspector');
    }
  });
  $('review-details').addEventListener('toggle', () => {
    if ($('review-details').open) { stopWork('inspector'); drawInspector(); }
    else { stopWork('playground'); start('playground'); }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { stopWork(); drawPlayground(); } });
  window.addEventListener('pagehide', () => stopWork());
  window.addEventListener('hashchange', openHash);
  new ResizeObserver(resizePlayground).observe($('playground'));
}
async function initialize() {
  bind();
  const audioEntries = ITEMS.flatMap(item => ['A', 'B'].map(variant => [`${item.id}/${variant}`, url(`candidates/audio-v1/${item.id}/${variant}.wav`)]));
  audioEntries.push(['reference', url('references/impact-baseball.wav')]);
  const audioLoading = audio.preload(audioEntries).then(errors => {
    $('audio-load-status').textContent = errors.length ? `음원 로딩 오류: ${errors.join(' / ')}` : '물건별 A/B 10개와 기존 야구공 음원 1개가 준비됐습니다. 버튼을 눌렀을 때만 소리를 냅니다.';
    $('audio-load-status').classList.toggle('error', errors.length > 0); updateAudioControls();
  });
  const failures = [];
  await Promise.all([
    ...CHARACTERS.map(async character => {
      const entry = { candidate: null, original: null }; sheets.set(character.id, entry);
      for (const source of ['candidate', 'original']) {
        const prefix = source === 'candidate' ? `candidates/character-v2/${character.id}` : `originals/${character.id}`;
        try {
          const [base, throwHit] = await Promise.all([image(`${prefix}/base.png`, 240, 24), image(`${prefix}/throw_hit.png`, 192, 24)]);
          entry[source] = { base, throw_hit: throwHit };
        } catch (error) { failures.push(`${source === 'candidate' ? '최신 후보' : '원본'} ${character.name}: ${error.message}`); }
      }
    }),
    ...ITEMS.map(async item => {
      try { objects.set(item.id, await image(`candidates/keepsakes-v2/${item.id}/sprite.png`, 192, 16)); }
      catch (error) { failures.push(`${item.name}: ${error.message}`); }
    }),
  ]);
  state.errors = failures;
  for (const character of CHARACTERS) {
    const button = element('button', null, 'character-card'); button.type = 'button'; button.dataset.character = character.id;
    const image = sheets.get(character.id)?.candidate?.base;
    if (image) button.append(spriteCopy(image, 0, 24, 3));
    else { button.append(element('small', '파일 오류')); button.disabled = true; }
    button.append(element('span', character.name), element('small', character.id === 'pixel_quokka' ? '새 쿼카' : '원본 외형'));
    button.setAttribute('aria-pressed', String(state.sender === character.id));
    button.addEventListener('click', () => selectSender(character.id)); $('sender-cards').append(button);
  }
  state.ready = CHARACTERS.every(character => sheets.get(character.id)?.candidate) && ITEMS.every(item => objects.has(item.id));
  $('load-status').textContent = failures.length ? failures.join('\n') + '\n누락한 최신 후보를 원본으로 대체하지 않습니다.' : '새 쿼카를 포함한 최신 캐릭터 90프레임 · 물건 60프레임이 준비됐습니다.';
  $('load-status').classList.toggle('error', failures.length > 0);
  $('playground-controls').disabled = $('inspector-controls').disabled = !state.ready;
  document.querySelectorAll('.character-card').forEach(button => { button.disabled = !state.ready; });
  for (const id of ['playground-play', 'reset', 'play', 'frame']) $(id).disabled = !state.ready;
  renderAppearances(); renderCharacterGrids(); renderItemGrids(); updateInspectorFrames(); drawInspector();
  resizePlayground(); resetActors(); drawPlayground(); renderSelection();
  if (state.ready && !$('review-details').open) start('playground');
  openHash();
  await Promise.all([audioLoading, loadCopy()]);
}
Object.defineProperty(window, 'sideyPreview', { value: Object.freeze({ snapshot: () => ({
  ready: state.ready, owner: state.owner, playing: state.playing, time: state.time,
  sender: state.sender, target: state.target, item: state.item, variant: state.variant,
  soundEnabled: state.soundEnabled, impactCount: state.impactCount,
  projectile: state.projectile ? { phase: state.projectile.phase, source: state.projectile.source, target: state.projectile.target,
    x: state.projectile.x, y: state.projectile.y } : null,
  actors: state.actors.map(actor => ({ id: actor.id, x: Math.round(actor.x), y: Math.round(actor.y), frame: actor.frame, motion: actor.motion })),
  audio: audio.snapshot(), errors: [...state.errors],
}) }), configurable: false, writable: false });
initialize().catch(error => { stopWork(); $('load-status').textContent = `미리보기 초기화 오류: ${error.message}`; $('load-status').classList.add('error'); });
