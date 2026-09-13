"use strict";

(() => {
  const CHARACTERS = [
    { id: "pixel_shiba", name: "시바견", direction: "뾰족한 귀 · 좁아지는 주둥이와 볼 · 말린 꼬리" },
    { id: "pixel_duck", name: "오리", direction: "넓은 부리 · 둥근 이마 · 짧은 날개와 물갈퀴" },
    { id: "pixel_poop", name: "똥", direction: "나선형 외곽 유지 · 발 연결과 피격 후 복귀" },
    { id: "pixel_tteokbokki", name: "떡볶이", direction: "떡과 소스 구분 유지 · 발 연결과 던지기 준비 자세" },
    { id: "pixel_quokka", name: "쿼카", direction: "떨어진 둥근 귀 · 볼과 웃는 입 · 작은 앞발과 세로 몸통" },
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
  const state = { character: CHARACTERS[0].id, motion: "idle", frame: 0, scale: 4,
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

  function frameCanvas(image, frame, { scale = 6, silhouette = false, baseline = false } = {}) {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 24 * scale;
    const context = canvas.getContext("2d");
    context.imageSmoothingEnabled = false;
    context.drawImage(image, frame * 24, 0, 24, 24, 0, 0, canvas.width, canvas.height);
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
    if (candidate) comparison.append(imageFigure(candidate, "실제 후보 · appearance-v1"));
    comparison.append(imageFigure(base, "원본 · 실루엣", true));
    if (candidate) comparison.append(imageFigure(candidate, "후보 · 실루엣", true));
    const unchanged = ["pixel_poop", "pixel_tteokbokki"].includes(character.id);
    const note = candidate
      ? (unchanged ? "기본 0번은 원작을 유지한 후보입니다. 다른 프레임의 발 연결·동작 수정은 이후 단계입니다." : "원본을 직접 수정한 실제 픽셀 후보입니다. 최종 외형 승인 대기입니다.")
      : "24×24 후보 파일이 없거나 규격이 다릅니다. 후보를 불러오기 전에는 원본만 표시합니다.";
    card.append(comparison, element("p", note, "pending"));
    $("appearance-list").append(card);
  }

  function motionFor(sheet, index) {
    return Object.keys(MOTIONS).find((key) => MOTIONS[key].sheet === sheet && MOTIONS[key].indices.includes(index));
  }

  function renderFrameSheet(character, sheet, image) {
    const group = element("div");
    const count = sheet === "base" ? 10 : 8;
    group.append(element("p", `${sheet} · ${count}프레임`, "frame-sheet-label"));
    const grid = element("div", null, "frame-grid");
    for (let index = 0; index < count; index++) {
      const motion = motionFor(sheet, index);
      const button = element("button", null, "frame-button");
      button.type = "button";
      button.dataset.character = character.id;
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
    const image = assets.get(state.character)?.[motion.sheet];
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
    $("frame-status").value = `${state.character} / ${motion.sheet} ${state.frame} / ${state.motion}`;
    stage.setAttribute("aria-label", `${CHARACTERS.find((item) => item.id === state.character).name} 원본 ${motion.label} ${state.frame}번, ${state.scale}배, ${$("edge").selectedOptions[0].textContent} 가장자리`);
    document.querySelectorAll(".frame-button[aria-pressed='true']").forEach((button) => button.setAttribute("aria-pressed", "false"));
    const active = document.querySelector(`.frame-button[data-character="${state.character}"][data-sheet="${motion.sheet}"][data-frame="${state.frame}"]`);
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
      state.playing = true;
      $("play").textContent = "일시정지";
      animationRequest = requestAnimationFrame(tick);
    });
    $("reset").addEventListener("click", reset);
    document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
    window.addEventListener("pagehide", pause);
  }

  function renderKeepsakeConcepts(src) {
    const concepts = [
      { name: "쿼카 · A 잎사귀", sound: "얇은 잎 파삭", crop: [645, 803, 188, 176], selected: false },
      { name: "쿼카 · B 풀 뭉치", sound: "부드러운 풀 퍽", crop: [1235, 802, 166, 176], selected: false },
      { name: "시바견 · B 테니스공", sound: "탄성 있는 통", crop: [1225, 111, 160, 145], selected: true },
      { name: "오리 · A 물방울", sound: "짧은 물방울 팝", crop: [685, 279, 123, 152], selected: true },
      { name: "똥 · A 휴지 뭉치", sound: "가벼운 종이 퍽", crop: [662, 448, 175, 160], selected: true },
      { name: "떡볶이 · B 어묵꼬치", sound: "가벼운 촵", crop: [1197, 632, 242, 151], selected: true, hideBoardLabel: true },
    ];
    for (const concept of concepts) {
      const card = element("figure", null, "keepsake-card");
      const [x, y, width, height] = concept.crop;
      const crop = element("div", null, "keepsake-crop");
      if (concept.hideBoardLabel) crop.classList.add("without-board-label");
      crop.style.aspectRatio = `${width} / ${height}`;
      const image = document.createElement("img");
      image.src = src;
      image.alt = `${concept.name} 콘셉트 확대`;
      image.style.width = `${1536 / width * 100}%`;
      image.style.left = `${-x / width * 100}%`;
      image.style.top = `${-y / height * 100}%`;
      crop.append(image);
      card.append(element("h4", concept.name), element("span", concept.selected ? "기획 선택됨" : "비교 대기 · 미선택", "badge"), crop,
        element("figcaption", `충돌음 방향: ${concept.sound}. 음원은 아직 제작 전입니다.`));
      $(concept.selected ? "selected-concepts" : "quokka-concepts").append(card);
    }
    $("selected-concepts").hidden = false;
    $("quokka-concepts").hidden = false;
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
      renderKeepsakeConcepts(concept.src);
    } else {
      $("concept-pending").textContent = "콘셉트 미리보기를 불러오지 못했습니다. concepts/keepsakes-v1.png 경로를 확인해 주세요.";
    }
  }

  async function initialize() {
    bindControls();
    const loaded = await Promise.all(CHARACTERS.map(async (character) => {
      const [base, throwHit, appearance] = await Promise.all([
        loadImage(`originals/${character.id}/base.png`),
        loadImage(`originals/${character.id}/throw_hit.png`),
        loadImage(`candidates/appearance-v1/${character.id}.png`),
      ]);
      if (!base || !throwHit || base.width !== 240 || base.height !== 24 || throwHit.width !== 192 || throwHit.height !== 24) return character.name;
      const candidate = appearance?.width === 24 && appearance.height === 24 ? appearance : null;
      assets.set(character.id, { base, throw_hit: throwHit, candidate });
      return null;
    }));
    const failed = loaded.filter(Boolean);
    for (const character of CHARACTERS) {
      const images = assets.get(character.id);
      if (!images) continue;
      renderAppearance(character, images.base, images.candidate);
      const group = element("article", null, "frame-group");
      group.append(element("h3", character.name), renderFrameSheet(character, "base", images.base), renderFrameSheet(character, "throw_hit", images.throw_hit));
      $("frame-list").append(group);
    }
    $("load-status").textContent = failed.length ? `원본 로딩 또는 규격 오류: ${failed.join(", ")}. 경로·PNG 규격을 확인해 주세요.` : "원본 10개 시트 · 90프레임을 불러왔습니다.";
    // Disable missing characters without substituting an unrelated sprite.
    Array.from($("character").options).forEach((option) => { option.disabled = !assets.has(option.value); });
    const first = CHARACTERS.find((item) => assets.has(item.id));
    if (first) {
      state.character = first.id;
      $("character").value = first.id;
      ["play", "reset", "frame"].forEach((id) => { $(id).disabled = false; });
      reset();
    }
    await loadConcepts();
  }
  initialize().catch(() => { $("load-status").textContent = "검토 페이지 초기화에 실패했습니다. 브라우저 콘솔과 로컬 파일 경로를 확인해 주세요."; pause(); });
})();
