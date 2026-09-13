#!/usr/bin/env python3
"""Reproduce the new quokka's full motion candidates from its exact appearance.

Default checks output bytes without writing. --write explicitly regenerates two
PNG sheets and quokka-motion.json. The user requested a complete preview before
final approval; this builder does not change any approval record or appearance.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from audit_frames import FRAME_NAMES, analyze_frame, parse_rgba_png
from build_appearance import encode_png

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "candidates/character-v2/pixel_quokka/appearance.png"
SOURCE_SHA = "3203ffeafdee5efd5cc9e1c357faaf1d4fd627968751754891ee7cb669e3707f"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fresh():
    return [["."] * 24 for _ in range(24)]


def clone(grid):
    return [row[:] for row in grid]


def line(grid, x, y, colors):
    require(0 <= x and x + len(colors) <= 24 and 0 <= y < 24, "pixel edit outside cell")
    grid[y][x:x + len(colors)] = list(colors)


def close_eyes(grid):
    for x in (7, 15):
        line(grid, x, 8, "bb")
        line(grid, x, 9, "oo")


def startled_eyes(grid):
    line(grid, 7, 8, "ob"); line(grid, 7, 9, "bo")
    line(grid, 15, 8, "bo"); line(grid, 15, 9, "ob")


def feet(grid, left=0, right=0):
    grid[20] = ["."] * 24
    for start in (6 + left, 14 + right):
        line(grid, start, 20, "oooo")
        center = start + 1
        # Raised walking/rebound bodies leave row 19 empty. A one-pixel dark
        # ankle connects each four-pixel foot while its baseline stays fixed.
        if grid[19][center] == ".":
            require(grid[18][center] != ".", "ankle must touch body above")
            grid[19][center] = "o"


def translate_body(base, dx=0, dy=0, foot_offsets=(0, 0)):
    result = fresh()
    for y in range(20):
        for x in range(24):
            if base[y][x] == ".":
                continue
            target_x, target_y = x + dx, y + dy
            # A downward squash replaces the final body rows, never the feet.
            if target_y >= 20:
                continue
            require(0 <= target_x < 24 and target_y >= 0, "body translation clips a pixel")
            result[target_y][target_x] = base[y][x]
    feet(result, *foot_offsets)
    return result


def resting_head(base, drop):
    result = fresh()
    for y in range(15):
        result[y + drop] = base[y][:]
    for y in range(15 + drop, 20):
        result[y] = base[y][:]
    feet(result)
    return result


def poses(base):
    blink = clone(base)
    close_eyes(blink)
    walk = [translate_body(base, foot_offsets=(-1, 0)),
            translate_body(base, dy=-1, foot_offsets=(0, -1)),
            translate_body(base, foot_offsets=(0, 1)),
            translate_body(base, dy=-1, foot_offsets=(1, 0))]
    doze = [clone(blink), translate_body(blink, dx=-1)]
    offline = [resting_head(blink, 4), resting_head(blink, 3)]

    ready = clone(base)
    # Lift both small front paws off their resting belly position.
    ready[16][7:17] = base[17][7:17]
    line(ready, 9, 15, "occo")
    windup = translate_body(base, dx=-1)
    line(windup, 2, 15, "oo")
    line(windup, 1, 16, "ocb")
    line(windup, 2, 17, "ob")
    release = translate_body(base, dx=1)
    line(release, 20, 15, "oo")
    line(release, 20, 16, "bco")
    line(release, 20, 17, "bo")
    shocked = clone(base)
    startled_eyes(shocked)
    hit = [shocked, translate_body(shocked, dy=2), translate_body(blink, dy=-1), clone(base)]
    return {"base": [clone(base), blink] + walk + doze + offline,
            "throw_hit": [ready, windup, release, clone(base)] + hit}


RULES = {
    "base": [
        "appearance.png 원본 기본 자세와 RGBA 완전 동일",
        "눈의 흰 하이라이트를 털색으로 닫고 짧은 수평 눈꺼풀 유지; 얼굴·웃는 입 고정",
        "왼발을 왼쪽 1px 디디며 오른발 고정",
        "몸통 1px 상승, 오른발을 왼쪽 1px 회수; 두 발목 연결 픽셀 추가",
        "오른발을 오른쪽 1px 디디며 왼발 고정",
        "몸통 1px 상승, 왼발을 오른쪽 1px 회수; 두 발목 연결 픽셀 추가",
        "눈을 감고 원래 자세에서 졸기",
        "눈을 감은 머리·몸을 왼쪽 1px 기울이며 졸기",
        "감은 눈·귀·웃는 주둥이를 보존한 머리를 4px 내려 웅크린 잠 자세",
        "잠든 머리를 1px 들어 호흡; 하체와 발 기준선 유지",
    ],
    "throw_hit": [
        "배 앞에 모인 두 앞발을 1px 들어 준비",
        "몸을 왼쪽 1px 기울이고 왼쪽 앞발을 뒤로 빼는 준비 동작",
        "몸을 오른쪽 1px 기울이고 오른쪽 앞발을 내밀어 방출",
        "원래 기본 자세로 복귀; 방출 앞발을 배 앞으로 회수",
        "양쪽 눈을 안쪽으로 찡그려 충돌 반응; 웃는 주둥이 유지",
        "찡그린 얼굴·몸을 아래 2px 눌러 충격 흡수; 발 y=20 고정",
        "눈을 감고 몸을 위 1px 반동; 발목을 연결하고 발 y=20 고정",
        "눈을 뜬 원래 기본 자세로 복귀",
    ],
}


def build():
    source_bytes = SOURCE.read_bytes()
    require(sha(source_bytes) == SOURCE_SHA, "appearance changed; review it before rebasing motion candidates")
    width, height, source_rgba = parse_rgba_png(SOURCE)
    require((width, height) == (24, 24), "appearance must be 24×24 RGBA")
    appearance_report = json.loads((ROOT / "quokka-v2.json").read_text())
    palette = {key: tuple(value) for key, value in appearance_report["palette"].items()}
    reverse = {value: key for key, value in palette.items()}
    base = [[reverse[tuple(source_rgba[(y * 24 + x) * 4:(y * 24 + x + 1) * 4])]
             for x in range(24)] for y in range(24)]
    outputs, sheets = {}, []
    source_colors = {tuple(source_rgba[index:index + 4]) for index in range(0, len(source_rgba), 4)}
    frame_sets = poses(base)
    all_frames = []
    for sheet, grids in frame_sets.items():
        encoded_frames, frames = [], []
        require(len(grids) == len(FRAME_NAMES[sheet]), "incorrect frame count")
        for index, grid in enumerate(grids):
            rgba = bytes(channel for row in grid for key in row for channel in palette[key])
            colors = {tuple(rgba[offset:offset + 4]) for offset in range(0, len(rgba), 4)}
            require(colors <= source_colors, f"new color introduced: {sheet}:{index}")
            audit = analyze_frame(rgba)
            require(audit["hard_alpha"] and audit["baseline_preserved"] and not audit["detached_baseline_row"],
                    f"invalid alpha/foot baseline: {sheet}:{index}")
            require(len(audit["alpha_component_sizes_8_connected"]) == 1, f"disconnected body or foot: {sheet}:{index}")
            require(not audit["cell_boundary_contacts"], f"cell boundary contact: {sheet}:{index}")
            if sheet == "base" and index == 0:
                require(rgba == source_rgba, "base frame 0 must remain pixel-identical to appearance")
            encoded_frames.append(rgba)
            all_frames.append((f"{sheet}:{index}", rgba))
            frames.append({"index": index, "state": FRAME_NAMES[sheet][index], "rgba_sha256": sha(rgba),
                           "rule": RULES[sheet][index], "bounds_inclusive": audit["bounds_inclusive"],
                           "baseline_row": audit["lowest_opaque_row"], "alpha_components_8_connected": 1,
                           "palette_preserved": True, "hard_alpha": True, "cell_boundary_contacts": {},
                           "changed_pixels_from_appearance": sum(rgba[offset:offset + 4] != source_rgba[offset:offset + 4]
                                                                 for offset in range(0, len(rgba), 4)),
                           "rows": ["".join(row) for row in grid]})
        groups = ((0, 2), (2, 6), (6, 8), (8, 10)) if sheet == "base" else ((0, 4), (4, 8))
        for first, end in groups:
            require(len(set(encoded_frames[first:end])) == end - first, f"duplicate poses within motion: {sheet}:{first}:{end}")
        joined = b"".join(frame[y * 24 * 4:(y + 1) * 24 * 4] for y in range(24) for frame in encoded_frames)
        path = ROOT / f"candidates/character-v2/pixel_quokka/{sheet}.png"
        png = encode_png(len(grids) * 24, 24, joined)
        outputs[path] = png
        sheets.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(png),
                       "dimensions": [len(grids) * 24, 24], "frames": frames})
    duplicates = [[left_id, right_id] for (left_id, left), (right_id, right) in itertools.combinations(all_frames, 2)
                  if left == right]
    report = {"schema_version": 1, "character_id": "pixel_quokka", "status": "pending_full_preview_approval",
              "source": SOURCE.relative_to(ROOT).as_posix(), "source_sha256": SOURCE_SHA,
              "authorship": "Codex native frame construction based on the new quokka-v2 appearance; no old PR quokka pixels",
              "authorization_scope": "사용자 최신 지시로 외형 최종 승인 전 전체 동작 미리보기 후보 제작 허용; 승인 기록은 변경하지 않음",
              "geometry": {"cell_size": [24, 24], "frame_count": 18, "bottom_opaque_row": 20,
                           "palette": "exact source palette", "color_space": "sRGB", "alpha": "hard"},
              "exact_cross_state_duplicates": duplicates,
              "duplicate_rationale": "같은 기본 복귀 자세와 감은 눈 졸기 자세의 상태 간 재사용; 각 동작 내부에는 중복 없음",
              "sheets": sheets,
              "limitations": ["프레임 연결·경계·해시 검증은 사용자 외형·움직임·합성 승인을 대신하지 않음",
                              "미리보기 전용 자료; 활성 앱·상품·음원·승인 기록을 변경하지 않음"]}
    outputs[ROOT / "quokka-motion.json"] = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        for path, encoded in build().items():
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(encoded)
            else:
                require(path.is_file() and path.read_bytes() == encoded, f"stale/missing output: {path.relative_to(ROOT)}")
        print(f"{'WROTE' if args.write else 'PASS (read-only)'}: new quokka 18 frames, exact appearance base 0, connected feet and fixed baseline; approval pending")
        return 0
    except (AssertionError, ValueError, KeyError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
