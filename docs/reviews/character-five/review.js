"use strict";

(() => {
  const CHARACTERS = [
    { id: "pixel_shiba", name: "시바견", direction: "원본 외형 유지 승인 · 발 연결과 던지기 동작 수정 검토" },
    { id: "pixel_duck", name: "오리", direction: "원본 외형 유지 승인 · 발 연결 수정 검토" },
    { id: "pixel_poop", name: "똥", direction: "원본 외형 유지 승인 · 발 연결 수정 검토" },
    { id: "pixel_tteokbokki", name: "떡볶이", direction: "원본 외형 유지 승인 · 발 연결과 던지기 동작 수정 검토" },
    { id: "pixel_quokka", name: "쿼카", direction: "새 외형 검토 대기 · 목도리 없는 따뜻한 갈색 · 둥근 귀와 웃는 입" },
  ];
  const KEEPSAKES = [
    { id: "tennis_ball", name: "시바견 · 테니스공" },
    { id: "rubber_duck", name: "오리 · 목욕용 고무 오리" },
    { id: "tissue_ball", name: "똥 · 휴지 뭉치" },
    { id: "fish_cake_skewer", name: "떡볶이 · 어묵꼬치" },
    { id: "leaf", name: "쿼카 · 잎사귀" },
  ];
  const MOTIONS = {
    idle: { sheet: "base", indices: [0, 1], duration: 0.55, label: "기본" },
    walk: { sheet: "base", indices: [2, 3, 4, 5], duration: 0.16, label: "걷기" },
    doze: { sheet: "base", indices: [6, 7], duration: 0.8, label: "졸기" },
    offline: { sheet: "base", indices: [8, 9], duration: 1.2, label: "잠" },
    throw: { sheet: "throw_hit", indices: [0, 1, 2, 3], duration: 0.1, label: "던지기" },
    hit: { sheet: "throw_hit", indices: [4, 5, 6, 7], duration: 0.11, label: "피격" },
  };
  const $ = (id) => document.getElementById(id);
  const assets = new Map();
  const state = { source: "candidate", character: CHARACTERS[0].id, motion: "idle", frame: 0, scale: 4,
    background: "checker", edge: "bottom", timing: "current", flip: false,
    silhouette: false, baseline: true, playing: false, elapsed: 0 };
  const stage = $("stage");
  const ctx = stage.getContext("2d");
  let animationRequest = null;
  let lastTick = null;
  let lastPaint = null;

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function loadImage(src) {
    return new Promise((resolve) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => resolve(null);
      image.src = src;
    });
  }

  function frameCanvas(image, frame, { scale = 6, silhouette = false, baseline = false, cell = 24 } = {}) {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = cell * scale;
    const context = canvas.getContext("2d");
    context.imageSmoothingEnabled = false;
    context.drawImage(image, frame * cell, 0, cell, cell, 0, 0, canvas.width, canvas.height);
    if (silhouette) {
      context.globalCompositeOperation = "source-in";
      context.fillStyle = "#172723";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.globalCompositeOperation = "source-over";
    }
    if (baseline) {
      context.fillStyle = "#287cc0";
      context.fillRect(0, 21 * scale, canvas.width, 1);
    }
    return canvas;
  }

  function imageFigure(image, label, silhouette = false) {
    const figure = element("figure");
    const canvas = frameCanvas(image, 0, { silhouette });
    if (silhouette) canvas.className = "silhouette-preview";
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", label);
    figure.append(canvas, element("figcaption", label));
    return figure;
  }

  function renderAppearance(character, base, candidate) {
    const card = element("article", null, "appearance-card");
    card.append(element("h3", character.name), element("p", character.id, "asset-id"),
      element("p", character.direction, "detail"));
    const comparison = element("div", null, "comparison");
    comparison.append(imageFigure(base, "실제 원본 · base 0"));
    if (candidate) comparison.append(imageFigure(candidate, character.id === "pixel_quokka" ? "새 외형 · character-v2" : "현재 선택 · 원본 유지"));
    comparison.append(imageFigure(base, "원본 · 실루엣", true));
    if (candidate) comparison.append(imageFigure(candidate, "후보 · 실루엣", true));
    const note = candidate
      ? (character.id === "pixel_quokka" ? "새로운 쿼카 외형은 승인 대기입니다. 전체 동작은 외형 승인 후 제작합니다." : "원본 기본 0번 유지가 승인되었습니다. 발 연결·동작을 수정한 전체 프레임의 승인은 별도입니다.")
      : "현재 24×24 외형 파일이 없거나 규격이 다릅니다. 원본만 표시합니다.";
    card.append(comparison, element("p", note, "pending"));
    $("appearance-list").append(card);
  }

  function motionFor(sheet, index) {
    return Object.keys(MOTIONS).find((key) => MOTIONS[key].sheet === sheet && MOTIONS[key].indices.includes(index));
  }

  function renderFrameSheet(character, sheet, image, source) {
    const group = element("div");
    const count = sheet === "base" ? 10 : 8;
    group.append(element("p", `${sheet} · ${count}프레임`, "frame-sheet-label"));
    const grid = element("div", null, "frame-grid");
    for (let index = 0; index < count; index++) {
      const motion = motionFor(sheet, index);
      const button = element("button", null, "frame-button");
      button.type = "button";
      button.dataset.character = character.id;
      button.dataset.source = source;
      button.dataset.sheet = sheet;
      button.dataset.frame = String(index);
      button.setAttribute("aria-label", `${character.name} ${sheet} ${index}번 ${MOTIONS[motion].label} 선택`);
      button.setAttribute("aria-pressed", "false");
      button.append(frameCanvas(image, index, { scale: 4, baseline: true }),
        element("span", `${index} · ${motion}`), element("span", MOTIONS[motion].label));
      button.addEventListener("click", () => {
        pause();
        state.character = character.id;
        state.motion = motion;
        state.frame = index;
        state.elapsed = 0;
        $("character").value = character.id;
        $("motion-select").value = motion;
        updateFrameOptions();
        renderStage();
        $("motion").scrollIntoView({ behavior: "auto" });
      });
      grid.append(button);
    }
    group.append(grid);
    return group;
  }

  function characterSource(character = state.character) {
    return state.source === "candidate" && assets.get(character)?.candidate ? "candidate" : "original";
  }

  function sourceLabel(character = state.character) {
    return characterSource(character) === "candidate" ? "수정 후보 · 동작 승인 대기" : "수정 전 원본";
  }

  function renderCharacterGrids() {
    $("frame-list").replaceChildren();
    let candidateCount = 0;
    let originalCount = 0;
    for (const character of CHARACTERS) {
      const entry = assets.get(character.id);
      if (!entry) continue;
      const source = characterSource(character.id);
      const images = entry[source];
      const group = element("article", null, "frame-group");
      const note = source === "original" && state.source === "candidate"
        ? (character.id === "pixel_quokka" ? "쿼카 새 외형은 승인 전이므로 원본 18프레임을 참고용으로 표시합니다." : "수정 시트를 불러오지 못해 원본 18프레임을 참고용으로 표시합니다.") : sourceLabel(character.id);
      group.append(element("h3", character.name), element("p", note, "pending"),
        renderFrameSheet(character, "base", images.base, source), renderFrameSheet(character, "throw_hit", images.throw_hit, source));
      $("frame-list").append(group);
      if (source === "candidate") candidateCount += 18;
      else originalCount += 18;
    }
    $("grid-status").textContent = `현재 표시: 수정 후보 ${candidateCount}프레임 · 수정 전 원본 ${originalCount}프레임. 자료 선택은 위 움직임 비교와 함께 바뀝니다.`;
  }

  function updateFrameOptions() {
    $("frame").replaceChildren(...MOTIONS[state.motion].indices.map((index) => new Option(String(index), String(index))));
    $("frame").value = String(state.frame);
  }

  function background() {
    ctx.fillStyle = state.background === "dark" ? "#202725" : "#faf9f4";
    ctx.fillRect(0, 0, stage.width, stage.height);
    if (state.background === "checker") {
      ctx.fillStyle = "#e0e5df";
      for (let y = 0; y < stage.height; y += 16) {
        for (let x = 0; x < stage.width; x += 16) {
          if ((x / 16 + y / 16) % 2 === 0) ctx.fillRect(x, y, 16, 16);
        }
      }
    }
  }

  function frameAt(elapsed) {
    const motion = MOTIONS[state.motion];
    if (state.motion === "idle" && state.timing === "proposal") return elapsed % 2.7 < 2.4 ? 0 : 1;
    const index = Math.floor(elapsed / motion.duration);
    if (["throw", "hit"].includes(state.motion) && index >= motion.indices.length) return null;
    return motion.indices[index % motion.indices.length];
  }

  function renderStage() {
    background();
    const motion = MOTIONS[state.motion];
    const source = characterSource();
    const image = assets.get(state.character)?.[source]?.[motion.sheet];
    if (!image) return;
    const sprite = frameCanvas(image, state.frame, { scale: state.scale, silhouette: state.silhouette, baseline: state.baseline });
    const size = sprite.width;
    const vertical = ["left", "right"].includes(state.edge);
    const trackLength = (vertical ? stage.height : stage.width) - size - 24;
    const travel = state.motion === "walk" ? state.elapsed * 22 * state.scale / 2 : 0;
    const phase = (trackLength / 2 + travel) % (2 * trackLength);
    const position = 12 + size / 2 + (phase <= trackLength ? phase : 2 * trackLength - phase);
    let x = position;
    let y = stage.height - size / 2 - 12;
    let angle = 0;
    if (state.edge === "top") { y = size / 2 + 12; angle = Math.PI; }
    if (state.edge === "left") { x = size / 2 + 12; y = position; angle = Math.PI / 2; }
    if (state.edge === "right") { x = stage.width - size / 2 - 12; y = position; angle = -Math.PI / 2; }
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.translate(Math.round(x), Math.round(y));
    ctx.rotate(angle);
    ctx.scale(state.flip ? -1 : 1, 1);
    ctx.drawImage(sprite, -size / 2, -size / 2);
    ctx.restore();
    $("frame").value = String(state.frame);
    $("frame-status").value = `${sourceLabel()} / ${state.character} / ${motion.sheet} ${state.frame} / ${state.motion}`;
    stage.setAttribute("aria-label", `${CHARACTERS.find((item) => item.id === state.character).name} ${sourceLabel()} ${motion.label} ${state.frame}번, ${state.scale}배, ${$("edge").selectedOptions[0].textContent} 가장자리`);
    document.querySelectorAll(".frame-button[aria-pressed='true']").forEach((button) => button.setAttribute("aria-pressed", "false"));
    const active = document.querySelector(`.frame-button[data-character="${state.character}"][data-source="${source}"][data-sheet="${motion.sheet}"][data-frame="${state.frame}"]`);
    active?.setAttribute("aria-pressed", "true");
  }

  function pause() {
    state.playing = false;
    if (animationRequest !== null) cancelAnimationFrame(animationRequest);
    animationRequest = null;
    lastTick = lastPaint = null;
    $("play").textContent = "재생";
  }

  function tick(now) {
    if (!state.playing) return;
    if (lastTick !== null) state.elapsed += (now - lastTick) / 1000;
    lastTick = now;
    if (lastPaint === null || now - lastPaint >= 1000 / 30 - 0.5) {
      lastPaint = now;
      const frame = frameAt(state.elapsed);
      if (frame === null) {
        pause();
        state.motion = "idle";
        state.frame = 0;
        state.elapsed = 0;
        $("motion-select").value = "idle";
        updateFrameOptions();
      } else state.frame = frame;
      renderStage();
    }
    if (state.playing) animationRequest = requestAnimationFrame(tick);
  }

  function reset() {
    pause();
    state.elapsed = 0;
    state.frame = MOTIONS[state.motion].indices[0];
    updateFrameOptions();
    renderStage();
  }

  function bindControls() {
    $("character").append(...CHARACTERS.map((item) => new Option(item.name, item.id)));
    $("character").addEventListener("change", (event) => { state.character = event.target.value; reset(); });
    $("source").addEventListener("change", (event) => { pause(); state.elapsed = 0; state.source = event.target.value; renderCharacterGrids(); renderStage(); });
    $("motion-select").addEventListener("change", (event) => { state.motion = event.target.value; reset(); });
    ["scale", "background", "edge", "timing"].forEach((key) => $(key).addEventListener("change", (event) => {
      state[key] = key === "scale" ? Number(event.target.value) : event.target.value;
      reset();
    }));
    ["flip", "silhouette", "baseline"].forEach((key) => $(key).addEventListener("change", (event) => {
      state[key] = event.target.checked;
      renderStage();
    }));
    $("frame").addEventListener("change", (event) => { pause(); state.frame = Number(event.target.value); state.elapsed = 0; renderStage(); });
    $("play").addEventListener("click", () => {
      if (state.playing) { pause(); return; }
      const motion = MOTIONS[state.motion];
      // Starting after manual frame selection preserves the selected frame.
      if (state.elapsed === 0) state.elapsed = state.motion === "idle" && state.timing === "proposal"
        ? (state.frame === 1 ? 2.4 : 0) : motion.indices.indexOf(state.frame) * motion.duration;
      pauseKeepsake();
      state.playing = true;
      $("play").textContent = "일시정지";
      animationRequest = requestAnimationFrame(tick);
    });
    $("reset").addEventListener("click", reset);
    document.addEventListener("visibilitychange", () => { if (document.hidden) { pause(); pauseKeepsake(); } });
    window.addEventListener("pagehide", () => { pause(); pauseKeepsake(); });
  }

  async function loadConcepts() {
    const board = await loadImage("candidates/appearance-v1/concept-board.png");
    if (board) {
      $("appearance-board-image").src = board.src;
      $("appearance-board").hidden = false;
      $("appearance-board-pending").hidden = true;
    }
    const concept = await loadImage("concepts/keepsakes-v1.png");
    if (concept) {
      $("concept-image").src = concept.src;
      $("concept-preview").hidden = false;
      $("concept-pending").hidden = true;

    } else {
      $("concept-pending").textContent = "콘셉트 미리보기를 불러오지 못했습니다. concepts/keepsakes-v1.png 경로를 확인해 주세요.";
    }
  }

  const keepsakeImages = new Map();
  const keepsakeState = { id: KEEPSAKES[0].id, motion: "rotation", frame: 0, scale: 8, background: "checker", elapsed: 0, playing: false };
  let keepsakeRequest = null;
  let keepsakeTick = null;
  let keepsakePaint = null;

  function keepsakeIndices() {
    return keepsakeState.motion === "rotation" ? [0, 1, 2, 3, 4, 5, 6, 7] : [8, 9, 10, 11];
  }

  function updateKeepsakeFrames() {
    $("keepsake-frame").replaceChildren(...keepsakeIndices().map((frame) => new Option(String(frame), String(frame))));
    $("keepsake-frame").value = String(keepsakeState.frame);
  }

  function drawKeepsake() {
    const canvas = $("keepsake-stage");
    const context = canvas.getContext("2d");
    context.fillStyle = keepsakeState.background === "dark" ? "#202725" : "#faf9f4";
    context.fillRect(0, 0, canvas.width, canvas.height);
    if (keepsakeState.background === "checker") {
      context.fillStyle = "#e0e5df";
      for (let y = 0; y < canvas.height; y += 16) {
        for (let x = 0; x < canvas.width; x += 16) {
          if ((x / 16 + y / 16) % 2 === 0) context.fillRect(x, y, 16, 16);
        }
      }
    }
    const image = keepsakeImages.get(keepsakeState.id);
    if (!image) return;
    const sprite = frameCanvas(image, keepsakeState.frame, { cell: 16, scale: keepsakeState.scale });
    context.imageSmoothingEnabled = false;
    context.drawImage(sprite, (canvas.width - sprite.width) / 2, (canvas.height - sprite.height) / 2);
    $("keepsake-frame").value = String(keepsakeState.frame);
    const label = `${KEEPSAKES.find((item) => item.id === keepsakeState.id).name} · ${keepsakeState.motion === "rotation" ? "회전" : "충돌"} ${keepsakeState.frame}번 · ${keepsakeState.scale}배`;
    $("keepsake-frame-status").value = label;
    canvas.setAttribute("aria-label", label);
    document.querySelectorAll(".keepsake-frame-button[aria-pressed='true']").forEach((button) => button.setAttribute("aria-pressed", "false"));
    document.querySelector(`.keepsake-frame-button[data-object="${keepsakeState.id}"][data-frame="${keepsakeState.frame}"]`)?.setAttribute("aria-pressed", "true");
  }

  function pauseKeepsake() {
    keepsakeState.playing = false;
    if (keepsakeRequest !== null) cancelAnimationFrame(keepsakeRequest);
    keepsakeRequest = null;
    keepsakeTick = keepsakePaint = null;
    $("keepsake-play").textContent = "반복 재생";
  }

  function animateKeepsake(now) {
    if (!keepsakeState.playing) return;
    if (keepsakeTick !== null) keepsakeState.elapsed += (now - keepsakeTick) / 1000;
    keepsakeTick = now;
    if (keepsakePaint === null || now - keepsakePaint >= 1000 / 30 - 0.5) {
      keepsakePaint = now;
      const indices = keepsakeIndices();
      keepsakeState.frame = indices[Math.floor(keepsakeState.elapsed / 0.1) % indices.length];
      drawKeepsake();
    }
    keepsakeRequest = requestAnimationFrame(animateKeepsake);
  }

  function bindKeepsakeControls() {
    $("keepsake-select").append(...KEEPSAKES.map((item) => new Option(item.name, item.id)));
    $("keepsake-select").addEventListener("change", (event) => {
      pauseKeepsake(); keepsakeState.id = event.target.value; keepsakeState.elapsed = 0;
      keepsakeState.frame = keepsakeIndices()[0]; drawKeepsake();
    });
    $("keepsake-motion").addEventListener("change", (event) => {
      pauseKeepsake(); keepsakeState.motion = event.target.value; keepsakeState.elapsed = 0;
      keepsakeState.frame = keepsakeIndices()[0]; updateKeepsakeFrames(); drawKeepsake();
    });
    $("keepsake-frame").addEventListener("change", (event) => {
      pauseKeepsake(); keepsakeState.frame = Number(event.target.value); keepsakeState.elapsed = 0; drawKeepsake();
    });
    $("keepsake-scale").addEventListener("change", (event) => { keepsakeState.scale = Number(event.target.value); drawKeepsake(); });
    $("keepsake-background").addEventListener("change", (event) => { keepsakeState.background = event.target.value; drawKeepsake(); });
    $("keepsake-play").addEventListener("click", () => {
      if (keepsakeState.playing) { pauseKeepsake(); return; }
      pause();
      if (keepsakeState.elapsed === 0) keepsakeState.elapsed = keepsakeIndices().indexOf(keepsakeState.frame) * 0.1;
      keepsakeState.playing = true;
      $("keepsake-play").textContent = "일시정지";
      keepsakeRequest = requestAnimationFrame(animateKeepsake);
    });
  }

  function renderKeepsakeSheet(item, image) {
    const group = element("article", null, "frame-group");
    group.append(element("h3", item.name), element("p", "기획 선택됨 · 실제 회전·충돌 프레임 승인 대기", "pending"));
    for (const motion of ["rotation", "impact"]) {
      const indices = motion === "rotation" ? [0, 1, 2, 3, 4, 5, 6, 7] : [8, 9, 10, 11];
      group.append(element("p", motion === "rotation" ? "회전 0–7" : "충돌 8–11", "frame-sheet-label"));
      const grid = element("div", null, "keepsake-frame-grid");
      for (const frame of indices) {
        const button = element("button", null, "keepsake-frame-button");
        button.type = "button";
        button.dataset.object = item.id;
        button.dataset.frame = String(frame);
        button.setAttribute("aria-pressed", "false");
        button.setAttribute("aria-label", `${item.name} ${motion === "rotation" ? "회전" : "충돌"} ${frame}번 선택`);
        button.append(frameCanvas(image, frame, { cell: 16, scale: 4 }), element("span", `${frame} · ${motion === "rotation" ? "회전" : "충돌"}`));
        button.addEventListener("click", () => {
          pauseKeepsake();
          keepsakeState.id = item.id; keepsakeState.motion = motion; keepsakeState.frame = frame; keepsakeState.elapsed = 0;
          $("keepsake-select").value = item.id; $("keepsake-motion").value = motion;
          updateKeepsakeFrames(); drawKeepsake();
          $("keepsake-stage").scrollIntoView({ behavior: "auto", block: "center" });
        });
        grid.append(button);
      }
      group.append(grid);
    }
    $("keepsake-frames").append(group);
  }

  async function loadKeepsakes() {
    const results = await Promise.all(KEEPSAKES.map(async (item) => {
      const image = await loadImage(`candidates/keepsakes-v2/${item.id}/sprite.png`);
      if (!image || image.width !== 192 || image.height !== 16) return item.name;
      keepsakeImages.set(item.id, image);
      return null;
    }));
    for (const item of KEEPSAKES) {
      const image = keepsakeImages.get(item.id);
      if (image) renderKeepsakeSheet(item, image);
    }
    const failed = results.filter(Boolean);
    $("keepsake-load-status").textContent = `물건 ${keepsakeImages.size}종 · ${keepsakeImages.size * 12}프레임 로딩 완료.`
      + (failed.length ? ` 파일 누락 또는 규격 오류: ${failed.join(", ")}.` : " 최종 그림·동작 승인 대기입니다.");
    Array.from($("keepsake-select").options).forEach((option) => { option.disabled = !keepsakeImages.has(option.value); });
    const first = KEEPSAKES.find((item) => keepsakeImages.has(item.id));
    if (first) {
      keepsakeState.id = first.id; $("keepsake-select").value = first.id;
      $("keepsake-play").disabled = false; $("keepsake-frame").disabled = false;
      updateKeepsakeFrames(); drawKeepsake();
    }
  }

  async function initialize() {
    bindControls();
    bindKeepsakeControls();
    const loaded = await Promise.all(CHARACTERS.map(async (character) => {
      const corrected = character.id === "pixel_quokka" ? [] : [
        loadImage(`candidates/character-v2/${character.id}/base.png`),
        loadImage(`candidates/character-v2/${character.id}/throw_hit.png`),
      ];
      const [base, throwHit, appearance, correctedBase, correctedHit] = await Promise.all([
        loadImage(`originals/${character.id}/base.png`),
        loadImage(`originals/${character.id}/throw_hit.png`),
        loadImage(`candidates/character-v2/${character.id}/appearance.png`),
        ...corrected,
      ]);
      if (!base || !throwHit || base.width !== 240 || base.height !== 24 || throwHit.width !== 192 || throwHit.height !== 24) return character.name;
      const pose = appearance?.width === 24 && appearance.height === 24 ? appearance : null;
      const candidate = correctedBase?.width === 240 && correctedBase.height === 24 && correctedHit?.width === 192 && correctedHit.height === 24
        ? { base: correctedBase, throw_hit: correctedHit } : null;
      assets.set(character.id, { original: { base, throw_hit: throwHit }, candidate, appearance: pose });
      return null;
    }));
    const failed = loaded.filter(Boolean);
    for (const character of CHARACTERS) {
      const images = assets.get(character.id);
      if (!images) continue;
      renderAppearance(character, images.original.base, images.appearance);
    }
    renderCharacterGrids();
    $("load-status").textContent = failed.length ? `원본 로딩 또는 규격 오류: ${failed.join(", ")}. 경로·PNG 규격을 확인해 주세요.` : `원본 10개 시트 · 90프레임, 수정 후보 ${Array.from(assets.values()).filter((item) => item.candidate).length * 18}프레임을 불러왔습니다. 쿼카 새 외형의 동작 시트는 아직 없습니다.`;
    // Disable missing characters without substituting an unrelated sprite.
    Array.from($("character").options).forEach((option) => { option.disabled = !assets.has(option.value); });
    const first = CHARACTERS.find((item) => assets.has(item.id));
    if (first) {
      state.character = first.id;
      $("character").value = first.id;
      ["play", "reset", "frame"].forEach((id) => { $(id).disabled = false; });
      reset();
    }
    await Promise.all([loadConcepts(), loadKeepsakes()]);
  }
  initialize().catch(() => { $("load-status").textContent = "검토 페이지 초기화에 실패했습니다. 브라우저 콘솔과 로컬 파일 경로를 확인해 주세요."; pause(); });
})();
