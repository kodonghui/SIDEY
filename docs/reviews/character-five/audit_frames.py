#!/usr/bin/env python3
"""Read-only audit of the five imported character sheets.

Default: recompute and verify source-audit.json. --write explicitly regenerates
that report; neither mode changes PNGs. --self-test checks detection boundaries.
Frame coordinates are zero-based with the origin at the top left.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent
REPOSITORY = PACKAGE.parents[2]
sys.path.insert(0, str(REPOSITORY / "scripts"))
from validate_pixel_assets import parse_rgba_png  # noqa: E402

CHARACTERS = ("pixel_shiba", "pixel_duck", "pixel_poop", "pixel_tteokbokki", "pixel_quokka")
FRAME_NAMES = {
    "base": ("idle_0", "idle_1", "walk_0", "walk_1", "walk_2", "walk_3",
             "doze_0", "doze_1", "offline_0", "offline_1"),
    "throw_hit": ("throw_0", "throw_1", "throw_2", "throw_3", "hit_0", "hit_1", "hit_2", "hit_3"),
}
REPORT = PACKAGE / "source-audit.json"
SIZE = 24
BASELINE = 20


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frame_bytes(pixels: bytes, width: int, index: int) -> bytes:
    return b"".join(pixels[(y * width + index * SIZE) * 4:
                           (y * width + (index + 1) * SIZE) * 4] for y in range(SIZE))


def component_sizes(opaque: set[tuple[int, int]]) -> list[int]:
    """8-neighbor alpha components; diagonal pixel connections count as joined."""
    remaining = set(opaque)
    sizes = []
    while remaining:
        pending = [remaining.pop()]
        count = 0
        while pending:
            x, y = pending.pop()
            count += 1
            for dx, dy in itertools.product((-1, 0, 1), repeat=2):
                neighbor = (x + dx, y + dy)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
        sizes.append(count)
    return sorted(sizes, reverse=True)


def analyze_frame(pixels: bytes) -> dict:
    if len(pixels) != SIZE * SIZE * 4:
        raise ValueError("frame must contain exactly 24×24 RGBA pixels")
    alpha_values = sorted(set(pixels[3::4]))
    opaque = {(i % SIZE, i // SIZE) for i, alpha in enumerate(pixels[3::4]) if alpha}
    rows = sorted({y for _, y in opaque})
    contacts = {
        "left": sorted(y for x, y in opaque if x == 0),
        "right": sorted(y for x, y in opaque if x == SIZE - 1),
        "top": sorted(x for x, y in opaque if y == 0),
        "bottom": sorted(x for x, y in opaque if y == SIZE - 1),
    }
    gaps = [y for y in range(min(rows), max(rows)) if y not in rows] if rows else []
    foot_x = sorted(x for x, y in opaque if y == BASELINE)
    # This identifies the specific full-row gap, not all possible detached feet.
    detached = BASELINE - 1 in gaps and bool(foot_x)
    return {
        "rgba_sha256": digest(pixels),
        "alpha_values": alpha_values,
        "hard_alpha": set(alpha_values) <= {0, 255},
        "opaque_pixel_count": len(opaque),
        "bounds_inclusive": [min(x for x, _ in opaque), min(rows),
                             max(x for x, _ in opaque), max(rows)] if opaque else None,
        "lowest_opaque_row": max(rows) if rows else None,
        "baseline_preserved": bool(rows) and max(rows) == BASELINE,
        "baseline_opaque_x": foot_x,
        "empty_rows_between_opaque_rows": gaps,
        "detached_baseline_row": detached,
        "alpha_component_sizes_8_connected": component_sizes(opaque),
        "cell_boundary_contacts": {side: points for side, points in contacts.items() if points},
        "clipping_assessment": "requires_visual_review" if any(contacts.values()) else "no_cell_boundary_contact",
    }


def duplicate_pairs(frames: list[tuple[str, bytes]]) -> list[list[str]]:
    return [[a, b] for (a, left), (b, right) in itertools.combinations(frames, 2) if left == right]


def build_report() -> dict:
    sheets = []
    duplicates = {}
    for character in CHARACTERS:
        character_frames = []
        for sheet, names in FRAME_NAMES.items():
            relative = f"originals/{character}/{sheet}.png"
            path = PACKAGE / relative
            width, height, pixels = parse_rgba_png(path)
            if (width, height) != (SIZE * len(names), SIZE):
                raise ValueError(f"{relative}: unexpected dimensions {width}×{height}")
            frames = []
            for index, name in enumerate(names):
                rgba = frame_bytes(pixels, width, index)
                character_frames.append((f"{sheet}:{index}", rgba))
                frames.append({"index": index, "state": name, **analyze_frame(rgba)})
            sheets.append({"path": relative, "file_sha256": digest(path.read_bytes()),
                           "dimensions": [width, height], "format": "8-bit RGBA, non-interlaced, sRGB",
                           "frames": frames})
        duplicates[character] = duplicate_pairs(character_frames)
    all_frames = [(sheet["path"], frame) for sheet in sheets for frame in sheet["frames"]]
    return {
        "schema_version": 1,
        "purpose": "원본 결함 조사; 품질 승인이나 수정본 승인 아님",
        "coordinates": "24×24 cell; zero-based x/y, top-left origin; bottom padding 3px means y=20",
        "hash_method": "PNG file bytes and decoded row-major 24×24 RGBA bytes; duplicates compare full RGBA bytes",
        "macos_reference": {
            "commit": "1480561350491bd7377b3cb925e453396b0fc961",
            "frame_contract": "macos/SIDEY/Features/PixelWorld/PixelCharacterCatalog.swift:4",
            "animation_timing": "macos/SIDEY/Features/PixelWorld/PixelWorldScene.swift:1307",
            "idle_seconds_per_frame": 0.55,
            "walk_seconds_per_frame": 0.16,
            "doze_seconds_per_frame": 0.8,
            "offline_seconds_per_frame": 1.2,
            "action_contract": "macos/SIDEY/Features/PixelWorld/PixelCharacterThrowCatalog.swift:159",
            "throw_total_seconds": 0.4,
            "hit_total_seconds": 0.44,
            "release_delay_seconds": 0.2,
            "frames_per_second": 30,
            "fps_source": "macos/SIDEY/Features/PixelWorld/PixelWorldScene.swift:30",
            "ordinary_maximum_speed_points_per_second": 22,
            "speed_source": "macos/SIDEY/Features/PixelWorld/PixelWorldSimulation.swift:111",
            "speed_note": "22pt/s is the ordinary speed limit; acceleration, idling and overlap change actual app speed.",
            "blink_timing_selection": "pending_user_approval; original PR timing not adopted",
        },
        "limitations": [
            "A full transparent row above baseline proves alpha separation, not artistic intent.",
            "8-neighbor components describe alpha connectivity, not semantic body/feet recognition.",
            "Cell boundary contact is a review flag, not proof of clipping; pixels outside a source cell are unavailable.",
            "Exact duplicate poses can be intentional across states; no duplicate is automatically removed.",
            "No visual approval, animation approval, app runtime verification or audio verification is implied.",
        ],
        "summary": {
            "sheet_count": len(sheets), "frame_count": len(all_frames),
            "hard_alpha_frame_count": sum(frame["hard_alpha"] for _, frame in all_frames),
            "baseline_preserved_frame_count": sum(frame["baseline_preserved"] for _, frame in all_frames),
            "detached_baseline_frames": [f"{path}:{frame['index']}" for path, frame in all_frames
                                         if frame["detached_baseline_row"]],
            "boundary_contact_frames": [f"{path}:{frame['index']}" for path, frame in all_frames
                                        if frame["cell_boundary_contacts"]],
        },
        "exact_duplicate_pairs_by_character": duplicates,
        "sheets": sheets,
    }


def self_test() -> None:
    def synthetic(points: set[tuple[int, int]], alpha: int = 255) -> bytes:
        frame = bytearray(SIZE * SIZE * 4)
        for x, y in points:
            offset = (y * SIZE + x) * 4
            frame[offset:offset + 4] = bytes((40, 80, 120, alpha))
        return bytes(frame)

    joined = synthetic({(10, 18), (10, 19), (10, 20)})
    separated = synthetic({(10, 18), (10, 20)})
    assert not analyze_frame(joined)["detached_baseline_row"]
    assert analyze_frame(separated)["detached_baseline_row"]
    assert analyze_frame(separated)["alpha_component_sizes_8_connected"] == [1, 1]
    assert analyze_frame(joined)["alpha_component_sizes_8_connected"] == [3]
    assert not analyze_frame(synthetic({(10, 21)}))["baseline_preserved"]
    assert not analyze_frame(synthetic({(10, 20)}, 128))["hard_alpha"]
    assert analyze_frame(synthetic({(0, 20)}))["clipping_assessment"] == "requires_visual_review"
    assert analyze_frame(joined)["cell_boundary_contacts"] == {}
    assert analyze_frame(bytes(SIZE * SIZE * 4))["bounds_inclusive"] is None
    assert duplicate_pairs([("a", joined), ("b", joined), ("c", separated)]) == [["a", "b"]]
    print("PASS: separation, connectivity, baseline drift, soft alpha, empty frame, boundary and duplicate detection")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="explicitly regenerate source-audit.json")
    group.add_argument("--self-test", action="store_true", help="run synthetic in-memory detector checks")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = build_report()
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        REPORT.write_text(encoded, encoding="utf-8")
        print("WROTE: source-audit.json (PNG files unchanged)")
    elif not REPORT.exists() or REPORT.read_text(encoding="utf-8") != encoded:
        print("FAIL: source-audit.json differs; inspect source changes before explicitly regenerating", file=sys.stderr)
        return 1
    else:
        print("PASS: 10 source PNGs and all 90 frame records match source-audit.json")
    summary = report["summary"]
    print(f"Findings: {len(summary['detached_baseline_frames'])} detached baseline frames, "
          f"{len(summary['boundary_contact_frames'])} boundary-contact frames; visual approval pending")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, ValueError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
