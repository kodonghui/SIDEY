// The page owns when audio may run; this module owns buffers, sources and cancellation.
export function createReviewAudio(onError = () => {}) {
  const bytes = new Map();
  const buffers = new Map();
  const sources = new Set();
  const errors = new Map();
  let context = null;
  let generation = 0;
  let decoding = 0;
  let started = 0;
  let totalScheduled = 0;

  function reconcile() {
    if (!context) return;
    for (const entry of sources) {
      if (!entry.counted && !entry.cancelled && context.currentTime >= entry.at) {
        entry.counted = true;
        started += 1;
      }
    }
  }
  function stop() {
    generation += 1;
    reconcile();
    for (const entry of sources) {
      entry.cancelled = true;
      entry.node.onended = null;
      try { entry.node.stop(); } catch { /* Already ended. */ }
      entry.node.disconnect();
    }
    sources.clear();
  }
  async function preload(entries) {
    await Promise.all(entries.map(async ([key, url]) => {
      try {
        const response = await fetch(url, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.arrayBuffer();
        if (data.byteLength < 44) throw new Error('WAV 데이터가 너무 짧습니다');
        bytes.set(key, data);
      } catch (error) {
        errors.set(key, `${key}: ${error.message}`);
      }
    }));
    return Array.from(errors.values());
  }
  async function unlock(keys) {
    const token = generation;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) throw new Error('이 브라우저에서 Web Audio를 지원하지 않습니다.');
    if (!context) context = new AudioContext();
    // Invoked synchronously from the click/change gesture before any awaits.
    await context.resume();
    decoding += 1;
    try {
      await Promise.all([...new Set(keys)].map(async key => {
        if (buffers.has(key)) return;
        if (!bytes.has(key)) throw new Error(`${key} 음원 파일이 없습니다.`);
        const decoded = await context.decodeAudioData(bytes.get(key).slice(0));
        buffers.set(key, decoded);
      }));
      return token === generation && context.state === 'running';
    } finally { decoding -= 1; }
  }
  function playPrepared(key, delay = 0) {
    if (!context || context.state !== 'running' || !buffers.has(key)) return false;
    reconcile();
    const node = context.createBufferSource();
    node.buffer = buffers.get(key);
    node.connect(context.destination);
    const entry = { node, at: context.currentTime + delay, counted: false, cancelled: false };
    sources.add(entry);
    node.onended = () => { reconcile(); sources.delete(entry); node.disconnect(); };
    node.start(entry.at);
    totalScheduled += 1;
    return true;
  }
  async function compare(keys, gap = 0.75) {
    stop();
    const token = generation;
    try {
      if (!await unlock(keys) || token !== generation) return false;
      let delay = 0;
      for (const key of keys) {
        playPrepared(key, delay);
        delay += buffers.get(key).duration + gap;
      }
      return true;
    } catch (error) {
      if (token === generation) onError(error.message);
      return false;
    }
  }
  return {
    preload, unlock, stop, compare, playPrepared,
    has: key => bytes.has(key),
    snapshot() {
      reconcile();
      const now = context?.currentTime ?? 0;
      return { started, totalScheduled,
        pending: [...sources].filter(entry => entry.at > now).length,
        active: [...sources].filter(entry => entry.at <= now).length,
        preparing: decoding, unlocked: context?.state === 'running' };
    },
  };
}
