#!/usr/bin/env python3
"""Reproduce the scarf-wearing quokka v3 review candidates; never change v2.

Default verifies output bytes. --write explicitly rebuilds the v3 candidates.
The source style is SIDEY's original quokka/hamster/shiba: small eyes with both
highlights on the same side, connected short limbs and a quiet blue scarf.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from audit_frames import FRAME_NAMES, analyze_frame, parse_rgba_png, frame_bytes
from build_appearance import encode_png

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'candidates/character-v3/pixel_quokka'
PALETTE = {
    '.': (0, 0, 0, 0), 'o': (46, 36, 25, 255), 'b': (164, 126, 84, 255),
    't': (191, 151, 108, 255), 's': (94, 80, 64, 255), 'c': (242, 230, 208, 255),
    'p': (242, 160, 140, 255), 'u': (127, 184, 232, 255), 'v': (74, 134, 184, 255),
}


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blank():
    return [['.'] * 24 for _ in range(24)]


def clone(grid):
    return [row[:] for row in grid]


def line(grid, y, x, colors):
    require(0 <= y < 24 and 0 <= x and x + len(colors) <= 24, 'drawing outside cell')
    grid[y][x:x + len(colors)] = list(colors)


def shape(grid, y, left, right, fill='b'):
    line(grid, y, left, 'o' + fill * (right - left - 1) + 'o')


def appearance():
    grid = blank()
    line(grid, 3, 5, 'ooo'); line(grid, 3, 16, 'ooo')
    line(grid, 4, 4, 'obpbo'); line(grid, 4, 15, 'obpbo')
    line(grid, 5, 4, 'obpboooooooobpbo')
    shape(grid, 6, 4, 19)
    shape(grid, 7, 3, 20)
    for y in range(8, 13): shape(grid, y, 2, 21)
    shape(grid, 13, 3, 20)
    shape(grid, 14, 3, 20, 'u'); shape(grid, 15, 3, 20, 'u')
    line(grid, 15, 16, 'vvv')
    for y in (16, 17): shape(grid, y, 4, 19)
    shape(grid, 18, 5, 18)
    line(grid, 19, 6, 'oooooooooooo')
    line(grid, 20, 6, 'ppp'); line(grid, 20, 15, 'ppp')
    # Match the source's two 2×2 dark eyes: same upper-left cream highlight
    # in both eyes. No opposite-facing whites or cream eye surrounds.
    line(grid, 9, 7, 'co'); line(grid, 9, 15, 'co')
    line(grid, 10, 7, 'oo'); line(grid, 10, 15, 'oo')
    line(grid, 11, 4, 'ptt'); line(grid, 11, 17, 'ttp')
    line(grid, 12, 5, 'ttt'); line(grid, 12, 16, 'ttt')
    line(grid, 11, 11, 'ss')
    line(grid, 12, 10, 's'); line(grid, 12, 13, 's')
    line(grid, 13, 11, 'ss')
    for y in (16, 17): line(grid, y, 8, 'cccccccc')
    line(grid, 18, 9, 'cccccc')
    # Tiny paws remain on the fur beside the belly, beneath the scarf.
    line(grid, 16, 6, 'sb'); line(grid, 16, 16, 'bs')
    return grid


def rgba(grid):
    return bytes(channel for row in grid for key in row for channel in PALETTE[key])


def eyes_closed(grid):
    for x in (7, 15):
        line(grid, 9, x, 'bb')
        line(grid, 10, x, 'oo')


def plant_feet(grid, offsets=(0, 0)):
    grid[20] = ['.'] * 24
    for x in (6 + offsets[0], 15 + offsets[1]):
        line(grid, 20, x, 'ppp')
        center = x + 1
        if grid[19][center] == '.':
            require(grid[18][center] != '.', 'ankle needs a body pixel directly above')
            grid[19][center] = 'p'


def body_pose(base, dx=0, dy=0, offsets=(0, 0)):
    result = blank()
    for y in range(20):
        for x in range(24):
            if base[y][x] == '.': continue
            nx, ny = x + dx, y + dy
            if ny >= 20: continue  # Compressed lower body, with fixed feet below.
            require(0 <= nx < 24 and ny >= 0, 'body shift clips a cell')
            result[ny][nx] = base[y][x]
    plant_feet(result, offsets)
    return result


def asleep(base, shift):
    result = blank()
    # Head AND both scarf rows move together. The blue scarf becomes the
    # blanket-like lower border of the tucked sleeping silhouette.
    for y in range(16):
        result[y + shift] = base[y][:]
    if shift == 3: result[19] = base[19][:]
    plant_feet(result)
    return result


def frame_sets(base):
    blink = clone(base); eyes_closed(blink)
    walk = [body_pose(base, offsets=(-1, 0)),
            body_pose(base, dy=-1, offsets=(0, -1)),
            body_pose(base, offsets=(0, 1)),
            body_pose(base, dy=-1, offsets=(1, 0))]
    ready = clone(base)
    line(ready, 16, 6, 'bb'); line(ready, 16, 16, 'bb')
    line(ready, 15, 6, 'sb'); line(ready, 15, 16, 'bs')
    windup = body_pose(base, dx=-1)
    line(windup, 15, 2, 'oo'); line(windup, 16, 1, 'otb'); line(windup, 17, 2, 'ob')
    release = body_pose(base, dx=1)
    line(release, 15, 20, 'oo'); line(release, 16, 20, 'bto'); line(release, 17, 20, 'bo')
    # Impact closes the normal horizontal eyelids; no angry/slanted or
    # inward-facing pupils are introduced, even in the impact frames.
    hit = [clone(blink), body_pose(blink, dy=2), body_pose(blink, dy=-1), clone(base)]
    return {'base': [clone(base), blink] + walk + [clone(blink), body_pose(blink, dx=-1),
                                                asleep(blink, 4), asleep(blink, 3)],
            'throw_hit': [ready, windup, release, clone(base)] + hit}


RULES = {
    'base': ['v3 appearance와 정확히 같은 기본 자세', '같은 위치의 작은 눈을 수평 눈꺼풀로 감음',
             '왼발 한 픽셀 내딛기', '몸·목도리 한 픽셀 상승, 오른발 회수, 발목 연결',
             '오른발 한 픽셀 내딛기', '몸·목도리 한 픽셀 상승, 왼발 회수, 발목 연결',
             '작은 감은 눈으로 졸기', '눈을 감은 몸·목도리를 왼쪽 한 픽셀 기울여 졸기',
             '머리와 파랑 목도리를 함께 4px 낮춘 웅크린 잠 자세',
             '목도리와 감은 눈을 유지한 잠 호흡: 머리 한 픽셀 상승'],
    'throw_hit': ['짧은 두 앞발을 한 픽셀 들어 준비', '몸·목도리 왼쪽 1px, 왼쪽 앞발 당기기',
                  '몸·목도리 오른쪽 1px, 짧은 오른쪽 앞발 방출', '기본 자세와 작은 앞발로 복귀',
                  '평범한 수평 눈꺼풀로 눈을 감으며 맞음; 찡그린 눈 없음',
                  '몸·목도리를 아래 2px 눌러 충격 흡수; 발은 y20 유지',
                  '감은 눈·목도리를 유지하며 몸 위 1px 반동, 발목 연결', '눈 뜬 기본 자세로 복귀'],
}


def scarf_connected(grid):
    remaining = {(x, y) for y, row in enumerate(grid) for x, key in enumerate(row) if key in ('u', 'v')}
    require(len(remaining) >= 20, 'blue scarf missing or too small')
    pending = [remaining.pop()]
    while pending:
        x, y = pending.pop()
        for dx, dy in itertools.product((-1, 0, 1), repeat=2):
            neighbor = x + dx, y + dy
            if neighbor in remaining:
                remaining.remove(neighbor); pending.append(neighbor)
    return not remaining


def build():
    base = appearance()
    pose_rgba = rgba(base)
    pose_png = encode_png(24, 24, pose_rgba)
    outputs = {TARGET / 'appearance.png': pose_png}
    artifacts = [{'path': (TARGET / 'appearance.png').relative_to(ROOT).as_posix(),
                  'sha256': sha(pose_png), 'role': 'appearance_pose', 'character_id': 'pixel_quokka',
                  'candidate_id': 'appearance-v3-pixel_quokka', 'dimensions': [24, 24]}]
    palette_values = set(PALETTE.values())
    sheets, all_frames = [], []
    for sheet, grids in frame_sets(base).items():
        encoded, records = [], []
        for index, grid in enumerate(grids):
            pixels = rgba(grid)
            audit = analyze_frame(pixels)
            require(audit['baseline_preserved'] and audit['hard_alpha'] and
                    len(audit['alpha_component_sizes_8_connected']) == 1 and
                    not audit['cell_boundary_contacts'] and not audit['detached_baseline_row'],
                    f'invalid geometry/connection: {sheet}:{index}')
            require(scarf_connected(grid), f'disconnected scarf: {sheet}:{index}')
            require({tuple(pixels[i:i+4]) for i in range(0, len(pixels), 4)} <= palette_values, 'new color introduced')
            if sheet == 'base' and index == 0:
                require(sum(key == 'c' for row in grid[:14] for key in row) == 2,
                        'only two matching eye highlights belong above the scarf')
            encoded.append(pixels); all_frames.append((f'{sheet}:{index}', pixels))
            records.append({'index': index, 'state': FRAME_NAMES[sheet][index], 'rgba_sha256': sha(pixels),
                            'rule': RULES[sheet][index], 'rows': [''.join(row) for row in grid],
                            'bounds_inclusive': audit['bounds_inclusive'], 'baseline_row': 20,
                            'hard_alpha': True, 'body_components_8_connected': 1, 'scarf_connected': True,
                            'scarf_pixel_count': sum(key in ('u', 'v') for row in grid for key in row),
                            'cell_boundary_contacts': {}})
        groups = ((0,2),(2,6),(6,8),(8,10)) if sheet == 'base' else ((0,4),(4,8))
        for start, end in groups:
            require(len(set(encoded[start:end])) == end-start, f'duplicate motion frames: {sheet}:{start}:{end}')
        if sheet == 'base': require(encoded[0] == pose_rgba, 'base0 must equal appearance')
        joined = b''.join(frame[y*24*4:(y+1)*24*4] for y in range(24) for frame in encoded)
        png = encode_png(24 * len(encoded), 24, joined)
        path = TARGET / f'{sheet}.png'; outputs[path] = png
        artifact = {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(png),
                    'role': 'character_sheet', 'character_id': 'pixel_quokka', 'sheet': sheet,
                    'candidate_id': f'character-v3-pixel_quokka-{sheet}', 'dimensions': [24 * len(encoded),24]}
        artifacts.append(artifact); sheets.append({**artifact, 'frames': records})
    sources = []
    for relative, label in [('docs/reviews/character-five/originals/pixel_quokka/base.png', '정지유 원본 쿼카 색·눈·목도리 스타일'),
                             ('assets/v1/characters/pixel_hamster/base.png', 'SIDEY 햄스터 눈 구조'),
                             ('docs/reviews/character-five/originals/pixel_shiba/base.png', '정지유 원본 시바 눈 구조')]:
        path = ROOT.parents[2] / relative
        sources.append({'path': path.relative_to(ROOT.parents[2]).as_posix(), 'sha256': sha(path.read_bytes()),
                        'frame': 0, 'use': label})
    duplicates = [[a, b] for (a, left), (b, right) in itertools.combinations(all_frames,2) if left == right]
    report = {'schema_version': 1, 'character_id': 'pixel_quokka', 'candidate_version': 'character-v3',
              'status': 'pending_user_appearance_and_motion_approval',
              'authorship': 'Codex의 새 픽셀 맵·동작. 정지유 원본 쿼카의 눈·목도리·팔레트 스타일 참조; v2 픽셀은 재사용하지 않음',
              'style_sources': sources,
              'direction': '양눈 동일한 좌상단 하이라이트, 작은 눈·4px 미소, 둥근 볼·짧은 팔다리·연결된 파랑 목도리',
              'palette': {key:list(value) for key,value in PALETTE.items()},
              'palette_changes_from_original_quokka': {'retained': ['o','s','c','p','u','v'],
                                                       'body': '회갈색을 따뜻한 갈색으로 변경', 'added': '볼을 위한 갈색 명암 한 단계'},
              'artifacts': artifacts, 'frame_count': 18, 'base0_equals_appearance': True,
              'exact_cross_state_duplicates': duplicates,
              'duplicate_rationale': 'idle 눈 감음/졸기/피격 첫 장면과 기본 복귀 자세는 정상적으로 재사용; 각 동작 내부 중복 없음',
              'sheets': sheets,
              'limitations': ['부모 제작 검토는 사용자 시각 승인 아님; 외형·전체 동작 승인 대기',
                              '기존 v2와 원본 파일·활성 앱·상품·승인 기록은 변경하지 않음']}
    outputs[ROOT / 'quokka-v3.json'] = (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    try:
        for path, encoded in build().items():
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(encoded)
            else:
                require(path.is_file() and path.read_bytes() == encoded, f'stale output: {path.relative_to(ROOT)}')
        print('WROTE' if args.write else 'PASS (read-only)')
    except (ValueError, KeyError, OSError) as error:
        print(f'FAIL: {error}', file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
