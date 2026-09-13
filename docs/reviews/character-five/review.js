import { CHARACTERS, ITEMS, MOTIONS, TIMING, frameAt, advanceWalk, flightDuration, projectilePoint } from './preview-state.js?v=asset-review-final';
import { createReviewAudio } from './review-audio.js?v=asset-review-final';

const $ = id => document.getElementById(id);
const url = path => `${path}?v=asset-review-final`;
const sheets = new Map(), objects = new Map(), copy = new Map(), spriteCache = new Map();
const cards = new Map();
const loadedCurrentPaths = [];
const SOUND_OPTIONS = {
  tennis_ball: ['1', '2', '3'], rubber_duck: ['original'], tissue_ball: ['1', '2'],
  fish_cake_skewer: ['1', '2', '3'], leaf: ['1', '2'],
};
const SELECTED_SOUNDS = { tennis_ball: '1', rubber_duck: 'original', tissue_ball: '2', fish_cake_skewer: '1', leaf: '1' };
function soundPath(item, sound) {
  if (['tennis_ball', 'fish_cake_skewer', 'rubber_duck'].includes(item)) return `candidates/audio-v2/${item}/${sound}.wav`;
  return `candidates/audio-v3/${item}/${sound === '1' ? 'A' : 'B'}.wav`;
}
const state = { ready: false, playing: false, owner: 'paused', epoch: 0, errors: [] };
const inspector = { character: CHARACTERS[0].id, source: 'candidate', motion: 'walk', frame: 2,
  scale: 4, background: 'checker', edge: 'bottom', timing: 'current', flip: false,
  silhouette: false, baseline: true, elapsed: 0 };
let request = null, lastTick = null, lastPaint = null;
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
function cancelTransient() {
  state.epoch += 1; audio.stop();
  for (const card of cards.values()) {
    if (card.composite) { card.composite = null; card.motion = 'rotation'; card.elapsed = 0; updateViewButtons(card); }
  }
}
function stopWork(owner = 'paused') {
  cancelTransient();
  if (request !== null) cancelAnimationFrame(request);
  request = null; lastTick = lastPaint = null; state.playing = false; state.owner = owner;
  updatePlaybackUI();
}
function start(owner = 'cards') {
  if (!state.ready || document.hidden) return;
  state.owner = owner; state.playing = true; lastTick = lastPaint = null;
  if (request !== null) cancelAnimationFrame(request);
  request = requestAnimationFrame(tick); updatePlaybackUI();
}
function updatePlaybackUI() {
  $('pause-all').textContent = state.playing && state.owner === 'cards' ? '일시정지' : '다시 재생';
  $('play').textContent = state.playing && state.owner === 'inspector' ? '일시정지' : '재생';
}
function tick(now) {
  if (!state.playing) return;
  const dt = lastTick === null ? 0 : Math.min(.1, (now - lastTick) / 1000); lastTick = now;
  if (state.owner === 'cards') {
    for (const card of cards.values()) {
      card.elapsed += dt;
      if (card.type === 'character' && card.motion === 'walk') Object.assign(card, advanceWalk(card, dt, card.canvas.width, 2));
    }
  } else if (state.owner === 'inspector') inspector.elapsed += dt;
  if (lastPaint === null || now - lastPaint >= 1000 / 30 - .5) {
    lastPaint = now;
    if (state.owner === 'cards') drawCards();
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
function cardBackdrop(card) {
  const context = card.canvas.getContext('2d');
  context.fillStyle = '#eff3e7'; context.fillRect(0, 0, card.canvas.width, 112);
  context.imageSmoothingEnabled = false;
  return context;
}
function drawComposite(card, context) {
  const scene = card.composite;
  const elapsed = card.elapsed;
  const left = 27, right = card.canvas.width - 27, y = 67;
  const flight = flightDuration(right - left);
  const collisionAt = TIMING.release + flight;
  const throwFrame = elapsed < TIMING.throwing ? frameAt('throw', elapsed) : 0;
  const sourceSheet = elapsed < TIMING.throwing ? 'throw_hit' : 'base';
  const hit = elapsed >= collisionAt && elapsed < collisionAt + TIMING.hit;
  const targetFrame = hit ? frameAt('hit', elapsed - collisionAt) : 0;
  context.drawImage(sprite(sheets.get(scene.source).candidate[sourceSheet], throwFrame), left - 24, y - 24);
  context.drawImage(sprite(sheets.get(scene.target).candidate[hit ? 'throw_hit' : 'base'], targetFrame), right - 24, y - 24);
  if (elapsed >= TIMING.release && elapsed < collisionAt) {
    const point = projectilePoint({ x: left, y: y - 5 }, { x: right, y: y - 5 }, (elapsed - TIMING.release) / flight);
    const frame = Math.floor((elapsed - TIMING.release) / TIMING.rotation) % 8;
    context.drawImage(sprite(objects.get(card.id), frame, 16, 2), Math.round(point.x - 16), Math.round(point.y - 16));
    card.frame = frame; card.x = point.x; card.y = point.y;
  }
  if (elapsed >= collisionAt && !scene.collided) {
    scene.collided = true; audio.playPrepared(`${card.id}/${scene.sound}`);
  }
  if (elapsed >= collisionAt && elapsed < collisionAt + TIMING.impact) {
    card.frame = 8 + Math.min(3, Math.floor((elapsed - collisionAt) / (TIMING.impact / 4)));
    context.drawImage(sprite(objects.get(card.id), card.frame, 16, 2), right - 16, y - 21);
  }
  if (elapsed >= collisionAt + TIMING.hit) {
    card.composite = null; card.motion = 'rotation'; card.elapsed = 0;
    updateViewButtons(card);
  }
}
function drawCards() {
  for (const card of cards.values()) {
    const context = cardBackdrop(card);
    if (card.type === 'character') {
      const spec = MOTIONS[card.motion];
      const elapsed = ['throw', 'hit'].includes(card.motion) ? card.elapsed % (spec.frames.length * spec.step) : card.elapsed;
      card.frame = frameAt(card.motion, elapsed);
      const x = card.motion === 'walk' ? Math.round(card.x) : Math.round(card.canvas.width / 2);
      card.y = 65;
      context.fillStyle = '#d8e4cb'; context.fillRect(0, 84, card.canvas.width, 1);
      context.save(); context.translate(x, card.y); context.scale(card.direction < 0 ? -1 : 1, 1);
      context.drawImage(sprite(sheets.get(card.id).candidate[spec.sheet], card.frame), -24, -24); context.restore();
      card.renderX = x;
    } else if (card.composite) drawComposite(card, context);
    else {
      card.frame = card.motion === 'impact' ? 8 + Math.floor(card.elapsed / .06) % 4 : Math.floor(card.elapsed / TIMING.rotation) % 8;
      card.x = card.canvas.width / 2; card.y = 56;
      context.drawImage(sprite(objects.get(card.id), card.frame, 16, 4), Math.round(card.x - 32), 24);
    }
    card.canvas.dataset.frame = String(card.frame); card.canvas.dataset.motion = card.motion;
  }
}
function resizeCards() {
  for (const card of cards.values()) {
    const width = Math.max(104, Math.floor(card.canvas.clientWidth));
    if (width !== card.canvas.width) { card.x = card.x * width / card.canvas.width; card.canvas.width = width; }
  }
  drawCards();
}
function setCardMode(card, mode) {
  cancelTransient(); card.motion = mode; card.elapsed = 0;
  if (card.type === 'item') updateViewButtons(card);
  if (state.owner !== 'cards' || !state.playing) { stopWork('cards'); start('cards'); }
  drawCards();
}
function updateViewButtons(card) {
  card.element.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === card.motion)));
}
async function playSound(card, sound) {
  // Sound comparisons replace audio only; the muted walking cards keep moving.
  cancelTransient(); card.sound = sound; updateAudioButtons();
  const epoch = state.epoch;
  card.element.querySelectorAll('.sound-button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.sound === sound)));
  $('audio-status').classList.remove('error');
  $('audio-status').textContent = `${ITEMS.find(item => item.id === card.id).name} · ${sound === 'original' ? '기존 소리' : `소리 ${sound}`}`;
  const played = await audio.compare([`${card.id}/${sound}`]);
  if (!played && epoch === state.epoch) $('audio-status').classList.add('error');
}
async function playComposite(card) {
  cancelTransient(); const epoch = state.epoch;
  try {
    if (!await audio.unlock([`${card.id}/${card.sound}`]) || epoch !== state.epoch) return;
    const index = CHARACTERS.findIndex(character => character.item === card.id);
    card.composite = { source: CHARACTERS[index].id, target: CHARACTERS[(index + 1) % CHARACTERS.length].id, sound: card.sound, collided: false };
    card.motion = 'composite'; card.elapsed = 0; updateViewButtons(card);
    if (state.owner !== 'cards' || !state.playing) start('cards');
  } catch (error) {
    if (epoch === state.epoch) { $('audio-status').textContent = error.message; $('audio-status').classList.add('error'); }
  }
}
function makeCard(id, type, name, parent) {
  const node = element('article', null, `review-card ${type === 'character' ? 'character' : 'keepsake'}-review-card`);
  node.dataset[type === 'character' ? 'character' : 'item'] = id;
  const canvas = element('canvas', null, `card-preview ${type === 'character' ? 'character' : 'keepsake'}-preview`);
  canvas.width = 180; canvas.height = 112; canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', `${name} 움직임 미리보기`);
  const description = element('p', '설명을 불러오는 중입니다.', 'card-description');
  node.append(canvas, element('h3', name), description);
  const card = { id, type, element: node, canvas, description, elapsed: 0, x: 90, y: 65, renderX: 90, direction: 1,
    motion: type === 'character' ? 'walk' : 'rotation', frame: type === 'character' ? 2 : 0,
    sound: type === 'item' ? SELECTED_SOUNDS[id] : null, composite: null };
  cards.set(id, card); $(parent).append(node); return card;
}
function renderCards() {
  for (const character of CHARACTERS) {
    if (!sheets.get(character.id)?.candidate) continue;
    const card = makeCard(character.id, 'character', character.name, 'character-cards');
    const label = element('label', null, 'card-controls'); label.append(element('span', '동작'));
    const select = element('select', null, 'character-motion'); select.setAttribute('aria-label', `${character.name} 동작`);
    select.append(...Object.entries(MOTIONS).map(([key, spec]) => new Option(spec.name, key)));
    select.addEventListener('change', event => setCardMode(card, event.target.value)); label.append(select); card.element.append(label);
  }
  for (const item of ITEMS) {
    if (!objects.has(item.id)) continue;
    const card = makeCard(item.id, 'item', item.name, 'keepsake-cards');
    const controls = element('div', null, 'card-controls'); const sounds = element('div', null, 'sound-buttons');
    card.element.append(element('p', item.id === 'rubber_duck' ? '기존 소리 확정' : `소리 ${SELECTED_SOUNDS[item.id]} 확정`, 'sound-selection'));
    for (const sound of SOUND_OPTIONS[item.id]) {
      const button = element('button', sound === 'original' ? '기존 소리 재생' : `소리 ${sound}`, 'sound-button');
      button.type = 'button'; button.dataset.sound = sound; button.disabled = !audio.has(`${item.id}/${sound}`);
      button.setAttribute('aria-label', `${item.name} ${sound === 'original' ? '기존 소리 재생' : `소리 ${sound} 재생`}`); button.setAttribute('aria-pressed', 'false');
      button.addEventListener('click', () => playSound(card, sound)); sounds.append(button);
    }
    const views = element('div', null, 'view-buttons');
    for (const [view, label] of [['rotation', '회전'], ['impact', '충돌'], ['composite', '던지는 모습']]) {
      const button = element('button', label); button.type = 'button'; button.dataset.view = view;
      button.addEventListener('click', () => view === 'composite' ? playComposite(card) : setCardMode(card, view)); views.append(button);
    }
    controls.append(sounds, views); card.element.append(controls); updateViewButtons(card);
  }
  resizeCards();
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
    const characterCard = cards.get(character.id); const itemCard = cards.get(character.item);
    if (characterCard) characterCard.description.textContent = entry.character.description;
    if (itemCard) itemCard.description.textContent = entry.keepsake.description;
    const group = element('article', null, 'copy-card');
    group.append(element('h3', `${entry.character.name} · ${entry.keepsake.name}`), element('p', entry.character.description), element('p', entry.keepsake.description, 'item-description'));
    $('copy-list').append(group);
  }
  if (failures.length) { $('copy-load-status').textContent = failures.join(' / '); $('copy-load-status').classList.add('error'); }
}
function openHash() {
  const id = location.hash.slice(1);
  if (['original-comparison', 'motion', 'frames', 'keepsake-frames-section', 'copy'].includes(id)) {
    $('review-details').open = true; stopWork('inspector');
    requestAnimationFrame(() => $(id).scrollIntoView({ block: 'start' }));
  } else if (['appearance', 'keepsakes'].includes(id)) {
    requestAnimationFrame(() => $(id).scrollIntoView({ block: 'start' }));
  }
}
function updateAudioButtons() {
  for (const item of ITEMS) {
    const card = cards.get(item.id); if (!card) continue;
    card.element.querySelectorAll('.sound-button').forEach(button => { button.disabled = !audio.has(`${item.id}/${button.dataset.sound}`); });
    card.element.querySelector('[data-view="composite"]').disabled = !state.ready || !audio.has(`${item.id}/${card.sound}`);
  }
}
function bind() {
  $('character').append(...CHARACTERS.map(item => new Option(item.name, item.id)));
  $('motion-select').append(...Object.entries(MOTIONS).map(([key, spec]) => new Option(spec.name, key)));
  $('pause-all').addEventListener('click', () => {
    const paused = !state.playing || state.owner !== 'cards'; stopWork('cards');
    if (paused) start('cards'); drawCards();
  });
  $('stop-audio').addEventListener('click', () => { cancelTransient(); $('audio-status').textContent = '소리를 멈췄습니다.'; drawCards(); });
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
    else { stopWork('cards'); start('cards'); }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { stopWork(); drawCards(); } });
  window.addEventListener('pagehide', () => stopWork());
  window.addEventListener('hashchange', openHash);
  new ResizeObserver(resizeCards).observe($('character-cards'));
}
async function initialize() {
  bind();
  const audioEntries = ITEMS.flatMap(item => SOUND_OPTIONS[item.id].map(sound => [`${item.id}/${sound}`, url(soundPath(item.id, sound))]));
  const audioLoading = audio.preload(audioEntries).then(errors => {
    $('audio-load-status').textContent = errors.length ? `음원 로딩 오류: ${errors.join(' / ')}` : '';
    $('audio-load-status').classList.toggle('error', errors.length > 0); updateAudioButtons();
  });
  const failures = [];
  await Promise.all([
    ...CHARACTERS.map(async character => {
      const entry = { candidate: null, original: null }; sheets.set(character.id, entry);
      for (const source of ['candidate', 'original']) {
        const version = character.id === 'pixel_quokka' ? 'character-v3' : 'character-v2';
        const prefix = source === 'candidate' ? `candidates/${version}/${character.id}` : `originals/${character.id}`;
        try {
          const [base, throwHit] = await Promise.all([image(`${prefix}/base.png`, 240, 24), image(`${prefix}/throw_hit.png`, 192, 24)]);
          entry[source] = { base, throw_hit: throwHit };
          if (source === 'candidate') loadedCurrentPaths.push(`${prefix}/base.png`, `${prefix}/throw_hit.png`);
        } catch (error) { failures.push(`${source === 'candidate' ? '최신 후보' : '원본'} ${character.name}: ${error.message}`); }
      }
    }),
    ...ITEMS.map(async item => {
      const path = `candidates/keepsakes-v2/${item.id}/sprite.png`;
      try { objects.set(item.id, await image(path, 192, 16)); loadedCurrentPaths.push(path); }
      catch (error) { failures.push(`${item.name}: ${error.message}`); }
    }),
  ]);
  state.errors = failures;
  state.ready = CHARACTERS.every(character => sheets.get(character.id)?.candidate) && ITEMS.every(item => objects.has(item.id));
  $('load-status').textContent = failures.length ? failures.join('\n') + '\n최신 후보가 없으면 원본으로 대체하지 않습니다.' : '';
  $('load-status').classList.toggle('error', failures.length > 0);
  $('inspector-controls').disabled = !state.ready;
  for (const id of ['pause-all', 'stop-audio', 'play', 'frame']) $(id).disabled = !state.ready;
  renderCards(); updateAudioButtons(); renderAppearances(); renderCharacterGrids(); renderItemGrids(); updateInspectorFrames(); drawInspector();
  if (state.ready && !$('review-details').open) start('cards');
  openHash();
  await Promise.all([audioLoading, loadCopy()]);
}
Object.defineProperty(window, 'sideyPreview', { value: Object.freeze({ snapshot: () => ({
  ready: state.ready, playing: state.playing, owner: state.owner,
  cards: [...cards.values()].map(card => ({ id: card.id, type: card.type, motion: card.motion, frame: card.frame,
    x: Math.round(card.type === 'character' ? card.renderX : card.x), y: Math.round(card.y) })),
  audio: audio.snapshot(), loadedCurrentPaths: [...loadedCurrentPaths], errors: [...state.errors],
}) }), writable: false, configurable: false });
initialize().catch(error => { stopWork(); $('load-status').textContent = `검토 페이지 오류: ${error.message}`; $('load-status').classList.add('error'); });
