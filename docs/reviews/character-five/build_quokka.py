#!/usr/bin/env python3
"""Rebuild the new quokka's single 24×24 approval pose, not an animation sheet."""
import hashlib
import json
import argparse
from pathlib import Path
from build_appearance import encode_png

ROOT = Path(__file__).resolve().parent
PALETTE = {
    ".": (0, 0, 0, 0),
    "o": (64, 39, 26, 255),
    "b": (166, 108, 65, 255),
    "s": (121, 75, 43, 255),
    "t": (207, 153, 97, 255),
    "c": (248, 221, 176, 255),
    "p": (229, 159, 125, 255),
    "w": (255, 248, 231, 255),
}
# The editable native drawing uses absolute cell coordinates to keep the face
# registered; this avoids half-pixel shifts from centering odd/even row widths.
def drawing():
    grid = [["."] * 24 for _ in range(24)]
    def line(y, x, colors):
        grid[y][x:x + len(colors)] = colors
    def shape(y, left, right, color="b"):
        line(y, left, "o" + color * (right - left - 1) + "o")
    line(2, 5, "ooo"); line(2, 16, "ooo")
    line(3, 4, "obpbo"); line(3, 15, "obpbo")
    line(4, 4, "obpbo"); line(4, 15, "obpbo")
    shape(5, 5, 18)
    shape(6, 4, 19)
    for y in range(7, 13): shape(y, 3, 20)
    shape(13, 4, 19)
    shape(14, 6, 17)
    shape(15, 5, 18)
    for y in (16, 17, 18): shape(y, 4, 19)
    shape(19, 5, 18, "s")
    line(20, 6, "oooo"); line(20, 14, "oooo")
    # Small bright eyes and large tan cheeks around a smiling cream muzzle.
    line(8, 7, "wo"); line(8, 15, "ow")
    line(9, 7, "oo"); line(9, 15, "oo")
    for y in (10, 11, 12): line(y, 5, "tttccccccccttt")
    line(13, 6, "ttcccccccctt")
    line(10, 11, "oo")
    line(11, 11, "oo")
    line(11, 8, "o"); line(11, 15, "o")
    line(12, 9, "o"); line(12, 14, "o")
    line(13, 10, "oooo")
    line(14, 8, "tcccccct")
    line(15, 7, "btcccccctb")
    line(16, 7, "bsoocc oosb".replace(" ", ""))
    line(17, 7, "btcccccctb")
    line(18, 7, "btcccccctb")
    line(19, 8, "btcccc tb".replace(" ", ""))
    return ["".join(row) for row in grid]


def build(write=False):
    grid = drawing()
    assert len(grid) == 24 and all(len(row) == 24 for row in grid)
    rgba = bytes(channel for row in grid for key in row for channel in PALETTE[key])
    target = ROOT / "candidates/character-v2/pixel_quokka/appearance.png"
    png = encode_png(24, 24, rgba)
    report = {
        "character_id": "pixel_quokka", "candidate_id": "appearance-v2-pixel_quokka",
        "path": target.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(png).hexdigest(),
        "status": "awaiting_appearance_approval", "authoring": "Codex native pixel map; ImageGen concept reference",
        "reference": "concepts/quokka-v2.png", "derived_from_original_pr_pixels": False,
        "direction": "기존 목도리·회갈색 외형을 재사용하지 않고 둥근 귀·갈색 털·웃는 주둥이·작은 앞발로 쿼카 재해석",
        "palette": {key: list(value) for key, value in PALETTE.items()}, "rows": grid,
        "frame_count": 1, "baseline_bottom_opaque_row": 20,
    }
    report_path = ROOT / "quokka-v2.json"
    encoded_report = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(png)
        report_path.write_bytes(encoded_report)
    else:
        if target.read_bytes() != png or report_path.read_bytes() != encoded_report:
            raise SystemExit("Quokka output differs; use --write to rebuild, then refresh hashes and approvals")
    print("Verified new 24×24 quokka appearance; animation requires appearance approval")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate the pose and report")
    build(parser.parse_args().write)
