// Pure geometry and frame timing for the local candidate preview.
export const CHARACTERS = [
  { id: 'pixel_shiba', name: '시바견', item: 'tennis_ball' },
  { id: 'pixel_duck', name: '오리', item: 'rubber_duck' },
  { id: 'pixel_poop', name: '똥', item: 'tissue_ball' },
  { id: 'pixel_tteokbokki', name: '떡볶이', item: 'fish_cake_skewer' },
  { id: 'pixel_quokka', name: '쿼카', item: 'leaf' },
];
export const ITEMS = [
  { id: 'tennis_ball', name: '테니스공' },
  { id: 'rubber_duck', name: '고무 오리' },
  { id: 'tissue_ball', name: '휴지 뭉치' },
  { id: 'fish_cake_skewer', name: '어묵꼬치' },
  { id: 'leaf', name: '잎사귀' },
];
export const MOTIONS = {
  walk: { sheet: 'base', frames: [2, 3, 4, 5], step: 0.16, name: '걷기' },
  idle: { sheet: 'base', frames: [0, 1], step: 0.55, name: '기본' },
  doze: { sheet: 'base', frames: [6, 7], step: 0.8, name: '졸기' },
  offline: { sheet: 'base', frames: [8, 9], step: 1.2, name: '잠' },
  throw: { sheet: 'throw_hit', frames: [0, 1, 2, 3], step: 0.1, name: '던지기' },
  hit: { sheet: 'throw_hit', frames: [4, 5, 6, 7], step: 0.11, name: '피격' },
};
export const TIMING = { release: 0.2, throwing: 0.4, hit: 0.44, impact: 0.24, rotation: 0.083 };
export function frameAt(motion, elapsed, timing = 'current') {
  if (motion === 'idle' && timing === 'proposal') return elapsed % 2.7 < 2.4 ? 0 : 1;
  const spec = MOTIONS[motion];
  const index = Math.floor(Math.max(0, elapsed) / spec.step);
  return spec.frames[['throw', 'hit'].includes(motion) ? Math.min(index, spec.frames.length - 1) : index % spec.frames.length];
}
export function advanceWalk(actor, seconds, width, scale) {
  const size = 24 * scale;
  const left = 12 + size / 2;
  const right = Math.max(left + 4, width - 12 - size / 2);
  let x = Math.max(left, Math.min(right, actor.x)) + actor.direction * seconds * 22 * scale / 2;
  let direction = actor.direction;
  // Reflect overshoot so movement speed is independent of refresh rate.
  while (x < left || x > right) {
    if (x > right) { x = right - (x - right); direction = -1; }
    if (x < left) { x = left + (left - x); direction = 1; }
  }
  return { x, direction };
}
export function flightDuration(distance, scale = 2) {
  return Math.min(0.95, Math.max(0.35, 0.35 + distance / (scale / 2) / 1600));
}
export function projectilePoint(start, target, fraction, scale = 2) {
  const t = Math.max(0, Math.min(1, fraction));
  const distance = Math.abs(target.x - start.x);
  const arc = Math.min(96, Math.max(24, distance / (scale / 2) * 0.18)) * scale / 2;
  return { x: start.x + (target.x - start.x) * t,
    y: start.y + (target.y - start.y) * t - 4 * arc * t * (1 - t) };
}
