#!/usr/bin/env python3
"""Reproduce four approved-original character repairs without changing sources.

Default verifies all checked-in outputs/report, read-only. --write explicitly
writes the twelve character-v2 PNGs and character-repairs.json. Appearance is
original base frame 0 exactly; animation approval remains separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from audit_frames import FRAME_NAMES, analyze_frame, frame_bytes, parse_rgba_png
from build_appearance import encode_png

ROOT = Path(__file__).resolve().parent
CHARACTERS = ("pixel_shiba", "pixel_duck", "pixel_poop", "pixel_tteokbokki")
REPORT = ROOT / "character-repairs.json"
TRANSPARENT = (0, 0, 0, 0)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unpack(frame: bytes) -> list[tuple[int, int, int, int]]:
    return [tuple(frame[index:index + 4]) for index in range(0, len(frame), 4)]


def pack(pixels: list[tuple[int, int, int, int]]) -> bytes:
    return bytes(channel for pixel in pixels for channel in pixel)


def bridge_feet(pixels: list[tuple[int, int, int, int]]) -> None:
    require(not any(pixels[19 * 24 + x][3] for x in range(24)), "expected entirely empty row 19")
    foot_x = [x for x in range(24) if pixels[20 * 24 + x][3]]
    runs = []
    for x in foot_x:
        if not runs or x != runs[-1][-1] + 1:
            runs.append([])
        runs[-1].append(x)
    require(len(runs) == 2 and all(len(run) == 3 for run in runs), "expected two three-pixel feet")
    for run in runs:
        x = run[1]
        require(pixels[18 * 24 + x][3] == 255, "bridge must connect body directly above the foot")
        pixels[19 * 24 + x] = pixels[20 * 24 + x]


def repair(character: str, sheet: str, index: int, original: bytes) -> tuple[bytes, list[str]]:
    pixels = unpack(original)
    reasons = []
    if (sheet == "base" and index in (1, 3, 5)) or (sheet == "throw_hit" and index == 6):
        bridge_feet(pixels)
        reasons.append("분리된 두 발의 가운데 x에 기존 발색으로 y=19 연결 픽셀을 하나씩 추가; 발 y=20 유지")
    if character == "pixel_shiba" and sheet == "throw_hit" and index == 2:
        # A connected forepaw extends from the right torso during release.
        # The next frame remains the original pose, showing the paw returning.
        outline = pixels[16 * 24 + 19]
        fur = pixels[16 * 24 + 18]
        cream = pixels[16 * 24 + 10]
        require(all(color[3] == 255 for color in (outline, fur, cream)), "expected original shiba torso palette")
        for x, y, color in ((19, 16, fur), (20, 16, outline),
                            (19, 17, fur), (20, 17, cream), (21, 17, outline),
                            (19, 18, outline), (20, 18, outline)):
            pixels[y * 24 + x] = color
        reasons.append("던지기 2번 방출 자세에 몸통과 연결된 작은 오른쪽 앞발을 2px 내밀고 3번은 원본 복귀 자세로 유지")
    if character == "pixel_tteokbokki" and sheet == "throw_hit" and index == 0:
        # Wind-up progression: one-pixel left lean, deeper left lean, release,
        # return. Translate the entire existing body, preserving facial pixels.
        for y in range(20):
            require(pixels[y * 24 + 23][3] == 0, "translation must not discard opaque pixels")
            row = pixels[y * 24:(y + 1) * 24]
            pixels[y * 24:(y + 1) * 24] = [TRANSPARENT] + row[:-1]
        reasons.append("던지기 0번 몸통 전체를 오른쪽 1px 이동해 1번보다 얕은 준비 기울기로 구분; 얼굴·떡·소스와 발 y=20 보존")
    return pack(pixels), reasons


def make_outputs() -> tuple[dict[str, bytes], dict]:
    source_audit = json.loads((ROOT / "source-audit.json").read_text())
    source_pins = {sheet["path"]: sheet["file_sha256"] for sheet in source_audit["sheets"]}
    outputs = {}
    characters = []
    for character in CHARACTERS:
        character_report = {"character_id": character, "appearance_source": "original base:0", "sheets": []}
        for sheet, names in FRAME_NAMES.items():
            source_relative = f"originals/{character}/{sheet}.png"
            source = ROOT / source_relative
            require(sha(source.read_bytes()) == source_pins[source_relative], f"original SHA changed: {source_relative}")
            width, height, rgba = parse_rgba_png(source)
            require((width, height) == (24 * len(names), 24), "unexpected source dimensions")
            repaired_frames = []
            frame_reports = []
            for index, state in enumerate(names):
                original = frame_bytes(rgba, width, index)
                updated, reasons = repair(character, sheet, index, original)
                before, after = unpack(original), unpack(updated)
                audit = analyze_frame(updated)
                require(set(after) <= set(before), f"new palette color: {character}/{sheet}:{index}")
                require(audit["hard_alpha"] and audit["baseline_preserved"] and not audit["detached_baseline_row"],
                        f"invalid alpha/baseline/foot bridge: {character}/{sheet}:{index}")
                require(len(audit["alpha_component_sizes_8_connected"]) == 1,
                        f"disconnected pixels remain: {character}/{sheet}:{index}")
                require(before[20 * 24:] == after[20 * 24:], f"foot baseline changed: {character}/{sheet}:{index}")
                edits = [{"x": offset % 24, "y": offset // 24, "from": list(left), "to": list(right)}
                         for offset, (left, right) in enumerate(zip(before, after)) if left != right]
                require(bool(edits) == bool(reasons), "every edit needs an explicit reason")
                if sheet == "base" and index == 0:
                    require(updated == original, "approved original appearance must remain exact")
                    appearance_path = f"candidates/character-v2/{character}/appearance.png"
                    outputs[appearance_path] = encode_png(24, 24, updated)
                    character_report["appearance"] = {
                        "path": appearance_path, "sha256": sha(outputs[appearance_path]),
                        "dimensions": [24, 24], "rgba_sha256": sha(updated),
                        "pixel_identical_to_original_base_0": True,
                    }
                repaired_frames.append(updated)
                frame_reports.append({
                    "index": index, "state": state, "source_rgba_sha256": sha(original),
                    "rgba_sha256": sha(updated), "changed_pixel_count": len(edits),
                    "reasons": reasons, "pixel_diff": edits,
                    "baseline_row": audit["lowest_opaque_row"],
                    "alpha_components_8_connected": len(audit["alpha_component_sizes_8_connected"]),
                    "boundary_contacts": audit["cell_boundary_contacts"],
                })
            if sheet == "throw_hit":
                require(len(set(repaired_frames[:4])) == 4, f"duplicate throw frames remain: {character}")
            joined = b"".join(frame[y * 24 * 4:(y + 1) * 24 * 4]
                              for y in range(24) for frame in repaired_frames)
            path = f"candidates/character-v2/{character}/{sheet}.png"
            outputs[path] = encode_png(width, height, joined)
            character_report["sheets"].append({
                "path": path, "sha256": sha(outputs[path]), "dimensions": [width, height],
                "source_path": source_relative, "source_sha256": source_pins[source_relative],
                "frames": frame_reports,
            })
        characters.append(character_report)
    frames = [frame for character in characters for sheet in character["sheets"] for frame in sheet["frames"]]
    report = {
        "schema_version": 1,
        "status": "original_appearance_selected_animation_repairs_pending_review",
        "coordinates": "zero-based 24×24 cell; top-left origin; foot baseline row 20",
        "scope": "시바·오리·똥·떡볶이 원본 외형 유지. 코드로 발 연결과 중복 던지기만 수정. 쿼카는 별도 작업.",
        "limitations": ["셀 경계 접촉만으로 원본 실루엣을 줄이지 않음; 실제 잘림·전체 움직임은 사용자 검토 필요",
                        "정적 무결성 통과는 동작 승인·앱 실행·출시 승인을 의미하지 않음"],
        "summary": {"characters": 4, "sheet_count": 8, "frame_count": len(frames),
                    "appearance_pose_count": 4, "changed_frames": sum(bool(frame["pixel_diff"]) for frame in frames),
                    "changed_pixels": sum(frame["changed_pixel_count"] for frame in frames),
                    "connected_frames": sum(frame["alpha_components_8_connected"] == 1 for frame in frames)},
        "characters": characters,
    }
    return outputs, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        outputs, report = make_outputs()
        encoded_report = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        outputs["character-repairs.json"] = encoded_report
        if args.write:
            for relative, encoded in outputs.items():
                target = ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(encoded)
        else:
            for relative, encoded in outputs.items():
                target = ROOT / relative
                require(target.is_file() and target.read_bytes() == encoded, f"stale/missing output: {relative}")
        print(("WROTE" if args.write else "PASS (read-only)") + ": " + json.dumps(report["summary"]))
        print("Original sheets unchanged; animation approval pending.")
        return 0
    except (AssertionError, KeyError, ValueError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
