#!/usr/bin/env python3
"""Build only the five 24×24 idle comparison poses; never change originals.

The user explicitly authorized code edits of original pixels on 2026-09-13.
No full animation sheet is generated before appearance approval.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2] / "scripts"))
from validate_pixel_assets import parse_rgba_png


def encode_png(width, height, rgba):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    rows = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"sRGB", b"\0") + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def build():
    reports = []
    for name in ["shiba", "duck", "poop", "tteokbokki", "quokka"]:
        source = ROOT / "originals" / f"pixel_{name}" / "base.png"
        width, _, rgba = parse_rgba_png(source)
        original = [tuple(rgba[(y * width + x) * 4:(y * width + x) * 4 + 4]) for y in range(24) for x in range(24)]
        pixels = original.copy()
        palette = list(dict.fromkeys(original))
        transparent = (0, 0, 0, 0)

        def put(x, y, color):
            pixels[y * 24 + x] = transparent if color == "." else palette[int(color, 36)]

        def row(y, start, colors):
            for dx, color in enumerate(colors):
                put(start + dx, y, color)

        def narrow(y, left, right):
            for x in range(left):
                put(x, y, ".")
            for x in range(right + 1, 24):
                put(x, y, ".")
            put(left, y, "1")
            put(right, y, "1")

        changes = []
        if name == "shiba":
            # Keep all facial pixels; move only outer cheeks/body and the tail.
            for y in range(9, 12):
                for x in range(21, 24):
                    put(x, y, ".")
            narrow(11, 3, 19)
            narrow(12, 3, 19)
            narrow(13, 4, 18)
            for y in (14, 15):
                narrow(y, 3, 19)
            for y in (16, 17):
                narrow(y, 4, 18)
            narrow(18, 5, 17)
            row(19, 5, "1111111111111.")
            # Attached clockwise curl, with one transparent pixel as its center.
            row(12, 20, "11")
            row(13, 19, "1551")
            row(14, 20, "1.1")
            row(15, 20, "141")
            row(16, 19, "151")
            row(17, 18, "11")
            changes = ["기존 뾰족한 귀·얼굴·팔레트 유지", "볼 아래와 몸통 외곽을 한 픽셀 안쪽으로 정리", "우측 셀 끝에 닿던 꼬리를 연결된 말린 꼬리로 변경; x=23 여백 확보"]
        elif name == "duck":
            row(12, 8, "16666661")
            row(13, 8, "17777771")
            row(16, 3, "1A3")
            row(16, 18, "3A1")
            row(17, 3, ".1A3")
            row(17, 17, "3A1.")
            row(20, 5, "6666")
            row(20, 15, "6666")
            changes = ["원작 둥근 이마·깃털·눈·색감 유지", "부리 좌우를 한 픽셀씩 넓힘", "날개 끝을 짧게 접고 발을 물갈퀴 형태로 넓힘"]
        elif name == "quokka":
            row(3, 5, "11")
            row(3, 17, "11")
            row(4, 4, "1331")
            row(4, 16, "1331")
            row(5, 4, "1221")
            row(5, 16, "1221")
            # Preserve eyes and smiling mouth exactly; taller silhouette comes
            # from slightly raised round ears and a narrower upright lower body.
            for y in (16, 17):
                narrow(y, 4, 18)
            narrow(18, 5, 17)
            row(19, 5, "1111111111111.")
            row(16, 6, "54")
            row(16, 16, "45")
            row(17, 6, "15")
            row(17, 16, "51")
            changes = ["떨어진 둥근 귀를 한 픽셀 높이고 연결 유지", "웃는 입·눈·목도리와 원작 팔레트 유지", "하체를 좁히고 작은 앞발 표시로 세로로 선 체형 보강"]
        else:
            changes = ["기본 0번은 결함이 없어 원본 픽셀 그대로 유지", "승인 후 base 1·3·5와 action 6 발 연결 수정 예정"]
            if name == "tteokbokki":
                changes.append("승인 후 throw 0=1 준비 자세 중복 수정 예정")
        encoded = bytes(channel for pixel in pixels for channel in pixel)
        target = ROOT / "candidates" / "appearance-v1" / f"pixel_{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encode_png(24, 24, encoded))
        assert set(pixels) <= set(original) | {transparent}, "new color introduced"
        assert max(i // 24 for i, pixel in enumerate(pixels) if pixel[3]) == 20
        reports.append({"character_id": f"pixel_{name}", "path": str(target.relative_to(ROOT)),
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "source": str(source.relative_to(ROOT)), "source_frame": 0,
                        "changed_pixel_count": sum(a != b for a, b in zip(original, pixels)),
                        "palette_preserved": True, "changes": changes,
                        "edits": [{"x": i % 24, "y": i // 24, "from": list(a), "to": list(b)}
                                  for i, (a, b) in enumerate(zip(original, pixels)) if a != b]})
    (ROOT / "appearance-changes.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Built 5 idle comparison poses; no full animation sheets; visual approval pending")


if __name__ == "__main__":
    build()
