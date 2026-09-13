#!/usr/bin/env python3
"""Build/recheck review-only 16×16 keepsake animation candidates.

Explicit pixel maps author the four selected concepts; no bitmap resampling of
the concept illustration is used. --write is the only source-mutating mode.
The existing bath duck is copied byte-for-byte, retaining its original frames.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from build_appearance import encode_png, parse_rgba_png

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[2]
SIZE = 16
EMPTY = (0, 0, 0, 0)
STATES = [f"rotation_{i * 45}" for i in range(8)] + [
    "impact_contact", "impact_squash", "impact_bounce", "impact_recover"]
# Fixed constants avoid libm/platform differences at the 45-degree samples.
DIAGONAL = 0.7071067811865476
ROTATIONS = [(1, 0), (DIAGONAL, DIAGONAL), (0, 1), (-DIAGONAL, DIAGONAL),
             (-1, 0), (-DIAGONAL, -DIAGONAL), (0, -1), (DIAGONAL, -DIAGONAL)]
CONCEPTS = {
    "tennis_ball": {
        "name": "테니스공", "character_id": "pixel_shiba", "offset": [3, 3],
        "palette": {"o": "46521E", "g": "ABD331", "l": "CBE54D", "s": "81AC29", "w": "FFF8D7"},
        "rows": ["...oooo...", ".oowlggoo.", ".olwwgggo.", "olllwgggso",
                 "olllwwggso", "ollggwggso", "olggwwgsso", ".ogwwgsso.", ".oowsssoo.", "...oooo..."],
        "impact": "탄성 있는 옆으로 눌림, 작은 튕김 표시, 소멸",
    },
    "tissue_ball": {
        "name": "휴지 뭉치", "character_id": "pixel_poop", "offset": [3, 3],
        "palette": {"o": "777470", "w": "FFFCF4", "l": "EAE7DD", "s": "C2BEB5", "d": "A09C94"},
        "rows": ["....oo....", "..oowlo...", ".owwwsloo.", ".olwwsslo.",
                 "olslwlwwlo", "owwsllswlo", ".owswlslo.", ".olwwsloo.", "..ollllo..", "...oooo..."],
        "impact": "구겨진 종이의 옆으로 눌림, 작은 종이 조각, 소멸",
    },
    "fish_cake_skewer": {
        "name": "어묵꼬치", "character_id": "pixel_tteokbokki", "offset": [3, 3],
        "palette": {"o": "6B492D", "g": "DCAA65", "l": "F5D293", "s": "BA8349", "w": "FFE7B5", "k": "B78850"},
        "rows": ["........ko", "......ook.", ".....owlso", "...oowllso", "..owgslgo.",
                 ".owwlso...", "olwlgso...", "olgsso....", ".okoo.....", "ok........"],
        "impact": "접힌 어묵의 작은 눌림, 반동과 짧은 접촉선, 소멸",
    },
    "leaf": {
        "name": "잎사귀", "character_id": "pixel_quokka", "offset": [3, 3],
        "palette": {"o": "315934", "g": "5E9D37", "l": "94C451", "s": "447A32", "w": "B4D26B"},
        "rows": [".......ooo", "....oooglo", "...ogglgo.", "..ogllgso.", ".ogllglso.",
                 ".ogwllgso.", ".olglgso..", ".olgsso...", ".olooo....", "oo........"],
        "impact": "잎의 짧은 접힘, 작은 잎 조각, 소멸",
    },
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pixel_map(spec: dict) -> list[tuple[int, int, int, int]]:
    palette = {key: tuple(bytes.fromhex(value)) + (255,) for key, value in spec["palette"].items()}
    result = [EMPTY] * (SIZE * SIZE)
    ox, oy = spec["offset"]
    assert len(spec["rows"]) == 10 and all(len(row) == 10 for row in spec["rows"])
    for y, row in enumerate(spec["rows"]):
        for x, key in enumerate(row):
            if key != ".":
                result[(y + oy) * SIZE + x + ox] = palette[key]
    return result


def rotate(base: list, index: int) -> list:
    """Inverse nearest-pixel rotation around the same half-pixel anchor."""
    cosine, sine = ROTATIONS[index]
    result = []
    for y, x in itertools.product(range(SIZE), repeat=2):
        dx, dy = x - 7.5, y - 7.5
        # Nearest source pixel; exact half ties round toward positive infinity.
        sx = math.floor(cosine * dx + sine * dy + 8)
        sy = math.floor(-sine * dx + cosine * dy + 8)
        result.append(base[sy * SIZE + sx] if 0 <= sx < SIZE and 0 <= sy < SIZE else EMPTY)
    return result


def squash(base: list, width: int, height: int) -> list:
    result = [EMPTY] * (SIZE * SIZE)
    left, top = (SIZE - width) // 2, (SIZE - height) // 2
    for y in range(height):
        for x in range(width):
            sx = 3 + x * 10 // width
            sy = 3 + y * 10 // height
            result[(top + y) * SIZE + left + x] = base[sy * SIZE + sx]
    return result


def round_ball_rotation(base: list, index: int, spec: dict) -> list:
    """The circular outline stays fixed while the asymmetric seam rotates."""
    result = rotate(base, index)
    outline = tuple(bytes.fromhex(spec["palette"]["o"])) + (255,)
    fill = tuple(bytes.fromhex(spec["palette"]["g"])) + (255,)
    for y, x in itertools.product(range(SIZE), repeat=2):
        i = y * SIZE + x
        if not base[i][3]:
            result[i] = EMPTY
        elif any(not base[(y + dy) * SIZE + x + dx][3]
                 for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))):
            result[i] = outline
        elif not result[i][3] or result[i] == outline:
            result[i] = fill
    return result


def impacts(base: list, spec: dict, key: str) -> list:
    contact = squash(base, 10, 9)
    compressed = squash(base, 12, 6)
    fragments = [EMPTY] * (SIZE * SIZE)
    # Three bounded fragments/short bounce marks, all gone in the final frame.
    colors = [tuple(bytes.fromhex(spec["palette"][key])) + (255,) for key in ("o", "l", "s")]
    for x, y, color in [(4, 6, 0), (5, 6, 1), (5, 7, 2), (10, 5, 0),
                        (11, 5, 1), (10, 6, 2), (8, 10, 0), (8, 11, 1)]:
        fragments[y * SIZE + x] = colors[color]
    if key in ("tennis_ball", "fish_cake_skewer"):
        # Solid toys/wood bounce intact; paper/leaves can scatter small pieces.
        fragments = squash(base, 6 if key == "tennis_ball" else 8, 6)
        for x, y in ((4, 11), (4, 12), (11, 11), (11, 12)):
            fragments[y * SIZE + x] = colors[0]
    return [contact, compressed, fragments, [EMPTY] * (SIZE * SIZE)]


def rgba(frame: list) -> bytes:
    return bytes(channel for pixel in frame for channel in pixel)


def inspect(frames: list) -> tuple[list, list]:
    reports = []
    for index, frame in enumerate(frames):
        points = [(x, y) for y, x in itertools.product(range(SIZE), repeat=2) if frame[y * SIZE + x][3]]
        center = [sum(p[i] for p in points) / len(points) for i in range(2)] if points else None
        reports.append({"index": index, "state": STATES[index], "rgba_sha256": sha(rgba(frame)),
                        "bounds_inclusive": [min(p[0] for p in points), min(p[1] for p in points),
                                             max(p[0] for p in points), max(p[1] for p in points)] if points else None,
                        "opaque_pixels": len(points), "alpha_centroid": [round(v, 4) for v in center] if center else None,
                        "alpha_centroid_distance_from_anchor": round(sum((v - 7.5) ** 2 for v in center) ** .5, 4) if center else None,
                        "cell_boundary_contact": any(x in (0, 15) or y in (0, 15) for x, y in points),
                        "hard_alpha": all(pixel[3] in (0, 255) for pixel in frame),
                        "intentional_empty": index == 11 and not points})
    duplicates = [[a, b] for a, b in itertools.combinations(range(len(frames)), 2) if frames[a] == frames[b]]
    return reports, duplicates


def build() -> dict[Path, bytes]:
    outputs = {}
    entries = []
    for key, spec in CONCEPTS.items():
        base = pixel_map(spec)
        frames = [(round_ball_rotation(base, index, spec) if key == "tennis_ball" else rotate(base, index))
                  for index in range(8)] + impacts(base, spec, key)
        pixels = b"".join(rgba(frame[y * SIZE:(y + 1) * SIZE]) for y in range(SIZE) for frame in frames)
        data = encode_png(SIZE * 12, SIZE, pixels)
        path = ROOT / "candidates" / "keepsakes-v2" / key / "sprite.png"
        outputs[path] = data
        reports, duplicates = inspect(frames)
        assert not duplicates, f"{key}: unintentional duplicate frames: {duplicates}"
        assert all(not frame["cell_boundary_contact"] for frame in reports), f"{key}: clipped cell edge"
        entries.append({"candidate_id": key, "character_id": spec["character_id"],
                        "path": str(path.relative_to(ROOT)), "sha256": sha(data),
                        "source": "build_keepsakes.py explicit pixel map; informed by approved concepts/keepsakes-v1.png",
                        "authorship": "Codex가 이번 검토용으로 작성한 픽셀 맵·회전·충돌 후보; 정지유 원본 아님",
                        "palette_hex": spec["palette"], "rotation_center": [7.5, 7.5],
                        "rotation_method": "inverse nearest pixel, clockwise 45 degrees, fixed anchor; no per-frame recentering"
                                           + ("; tennis ball circular outline held fixed and seam rotated" if key == "tennis_ball" else ""),
                        "impact_description": spec["impact"], "frames": reports,
                        "exact_duplicate_pairs": duplicates, "approval_status": "pending_visual_rotation_impact_approval"})

    source = REPOSITORY / "assets/v1/throwables/throwable_squeaky_duck/sprite.png"
    data = source.read_bytes()
    assert sha(data) == "3b6935398d41b6d1cd5efa922392dbf4864782deb9880c5d0f10885e00906e7a", "review changed duck source first"
    width, height, pixels = parse_rgba_png(source)
    assert (width, height) == (192, 16)
    frames = [[tuple(pixels[(y * width + index * SIZE + x) * 4:(y * width + index * SIZE + x) * 4 + 4])
               for y, x in itertools.product(range(SIZE), repeat=2)] for index in range(12)]
    reports, duplicates = inspect(frames)
    path = ROOT / "candidates/keepsakes-v2/rubber_duck/sprite.png"
    outputs[path] = data
    entries.append({"candidate_id": "rubber_duck", "character_id": "pixel_duck",
                    "path": str(path.relative_to(ROOT)), "sha256": sha(data),
                    "source": str(source.relative_to(REPOSITORY)), "source_sha256": sha(data),
                    "authorship": "기존 SIDEY 삑삑 오리의 변경 없는 검토용 복사; 신규 창작·정지유 기여로 표시하지 않음",
                    "palette_hex": sorted({bytes(pixel[:3]).hex().upper() for frame in frames for pixel in frame if pixel[3]}),
                    "rotation_center": [7.5, 7.5], "rotation_method": "existing source frames unchanged",
                    "frames": reports, "exact_duplicate_pairs": duplicates,
                    "duplicate_rationale": "기존 자산의 정확한 복사이므로 중복을 자동 수정하지 않음; 최종 회전·충돌 승인 필요",
                    "approval_status": "pending_visual_rotation_impact_approval"})
    report = {"schema_version": 1, "candidate_version": "keepsakes-v2",
              "purpose": "선택된 애착 물건의 그림·회전·충돌 승인 후보; 음원·합성·출시 승인 아님",
              "format": {"cell_size": [16, 16], "sheet_size": [192, 16], "frames_per_sheet": 12,
                         "color_space": "sRGB", "alpha": "hard", "filtering": "nearest"},
              "license": "SIDEY Paid Asset License 1.0; review package LICENSE.md scope extension",
              "concept_source_sha256": sha((ROOT / "concepts/keepsakes-v1.png").read_bytes()),
              "limitations": ["알파 무게중심은 모양·텍스처에 따라 회전하며 고정 회전축과 동일하지 않음; 흔들림 최종 판단은 루프 검토 필요",
                              "신규 4종의 마지막 충돌 프레임은 의도된 완전 투명 소멸. 회전 프레임에는 빈 셀 없음",
                              "목욕 오리는 기존 삑삑 오리 자산의 변경 없는 후보 재사용; 별도 상품 생성·활성 manifest 변경 없음",
                              "음원 생성·복사·활성 자산 변경·앱 실행 검증은 수행하지 않음"],
              "items": entries}
    outputs[ROOT / "keepsake-changes.json"] = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="explicitly regenerate candidate sheets and change report")
    args = parser.parse_args()
    for path, data in build().items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        elif not path.exists() or path.read_bytes() != data:
            print(f"FAIL: stale/missing {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
    print(f"{'WROTE' if args.write else 'PASS'}: 5 keepsakes, 60 deterministic frames; visual approval pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
