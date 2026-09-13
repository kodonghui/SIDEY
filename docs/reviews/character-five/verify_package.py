#!/usr/bin/env python3
"""Validate review integrity; --require-approved additionally enforces final readiness.

No files are written. Current concept boards are presentation art, not production
pixel sheets. Passing the default check never establishes approval or readiness.
Future final artifacts use character_id, character_sheet.sheet=base|throw_hit and
audio_candidate.variant follows the per-character AUDIO_VARIANTS mapping. Audio metadata uses duration_seconds, peak, rms
(normalized linear amplitude), source and license. Approval evidence must quote
an actual user decision; software can validate its structure, not its truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import wave
import zlib

sys.dont_write_bytecode = True
from audit_frames import CHARACTERS, FRAME_NAMES, analyze_frame, frame_bytes, parse_rgba_png

PACKAGE = Path(__file__).resolve().parent
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif",
                  ".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".mp4", ".webm"}
FINAL_ROLES = {"appearance_pose", "character_sheet", "keepsake_sheet", "audio_candidate", "content_copy"}
ROLES = FINAL_ROLES | {"original_sheet", "concept_board", "composite_preview", "audio_reference", "audio_archive", "archived_sprite"}
AUDIO_VARIANTS = {"pixel_shiba": ("1", "2", "3"), "pixel_duck": ("original",),
                  "pixel_poop": ("A", "B"), "pixel_tteokbokki": ("1", "2", "3"), "pixel_quokka": ("A", "B")}
CHARACTER_STAGES = {"keepsake_plan", "appearance_pixels", "character_frames", "character_motion",
                    "keepsake_visual", "audio", "composite", "descriptions"}
EXPECTED_RECORDS = {(stage, character) for stage in CHARACTER_STAGES for character in CHARACTERS}
EXPECTED_RECORDS |= {("appearance_direction", "all"), ("idle_timing", "all")}
PREDECESSORS = {
    "appearance_pixels": ("appearance_direction",), "character_frames": ("appearance_pixels",),
    "character_motion": ("character_frames",), "keepsake_visual": ("keepsake_plan",),
    "audio": ("keepsake_visual",), "composite": ("character_motion", "audio"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def safe_path(root: Path, relative: object) -> Path:
    require(nonempty(relative), "artifact path must be a nonempty relative path")
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in relative
            and str(path) == relative and ":" not in relative, f"unsafe artifact path: {relative}")
    result = root / relative
    require(not result.is_symlink() and result.resolve().is_relative_to(root.resolve()),
            f"artifact escapes package or is a symlink: {relative}")
    require(result.is_file(), f"missing artifact: {relative}")
    return result


def png_dimensions(path: Path) -> list[int]:
    """Check PNG chunks/CRC and IHDR without requiring concept boards to be RGBA."""
    data = path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"invalid PNG: {path.name}")
    offset, dimensions, ended = 8, None, False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        require(offset + 12 + size <= len(data), f"truncated PNG: {path.name}")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = struct.unpack_from(">I", data, offset + 8 + size)[0]
        require(zlib.crc32(kind + payload) & 0xFFFFFFFF == crc, f"PNG CRC mismatch: {path.name}")
        if dimensions is None:
            require(kind == b"IHDR" and size == 13, f"PNG missing IHDR: {path.name}")
            dimensions = list(struct.unpack_from(">II", payload))
            require(all(n > 0 for n in dimensions), f"PNG empty dimensions: {path.name}")
        offset += 12 + size
        if kind == b"IEND":
            require(size == 0 and offset == len(data), f"PNG trailing data: {path.name}")
            ended = True
            break
    require(ended, f"PNG missing IEND: {path.name}")
    return dimensions


def validate_pixels(path: Path, artifact: dict) -> None:
    role = artifact["role"]
    if role == "concept_board" or role == "composite_preview":
        return
    width, height, rgba = parse_rgba_png(path)
    require(set(rgba[3::4]) == {0, 255}, f"hard alpha required: {artifact['path']}")
    if role == "archived_sprite":
        return
    if role == "original_sheet":
        names = FRAME_NAMES[path.stem]
        require((width, height) == (24 * len(names), 24), "wrong original sheet dimensions")
        return  # Known source defects are preserved and audited, not silently corrected.
    if role == "keepsake_sheet":
        require((width, height) == (192, 16), "keepsake_sheet must contain twelve 16×16 frames")
        frames = [b"".join(rgba[(row * width + index * 16) * 4:
                                  (row * width + (index + 1) * 16) * 4] for row in range(16))
                  for index in range(12)]
        require(all(any(frame[3::4]) for frame in frames[:8]), "empty keepsake rotation frame")
        duplicates = [[left, right] for left in range(12) for right in range(left + 1, 12)
                      if (left < 8) == (right < 8) and frames[left] == frames[right]]
        require(artifact.get("intentional_duplicate_pairs", []) == duplicates,
                "keepsake duplicate frames must be explicitly documented for visual approval")
        return
    sheet = artifact.get("sheet")
    count = len(FRAME_NAMES[sheet]) if role == "character_sheet" else 1
    require((width, height) == (24 * count, 24), f"wrong production dimensions: {artifact['path']}")
    frames = [frame_bytes(rgba, width, index) for index in range(count)]
    for index, frame in enumerate(frames):
        audit = analyze_frame(frame)
        require(audit["baseline_preserved"], f"baseline drift: {artifact['path']}:{index}")
        require(not audit["detached_baseline_row"], f"detached foot row: {artifact['path']}:{index}")
    if role == "character_sheet" and sheet == "throw_hit":
        require(len(set(frames[:4])) == 4, f"duplicate throw poses: {artifact['path']}")


def validate_audio(path: Path, artifact: dict) -> None:
    require(path.suffix.lower() == ".wav", "audio candidates must be WAV")
    require(nonempty(artifact.get("source")), "audio candidate requires source attribution")
    with wave.open(str(path), "rb") as sound:
        require((sound.getframerate(), sound.getsampwidth(), sound.getnchannels(), sound.getcomptype())
                == (48000, 2, 1, "NONE"), f"expected 48kHz 16-bit mono PCM: {path.name}")
        count = sound.getnframes()
        require(count > 0, f"empty audio: {path.name}")
        data = sound.readframes(count)
    require(len(data) == count * 2, f"truncated audio: {path.name}")
    samples = struct.unpack(f"<{count}h", data)
    require(all(-32768 < sample < 32767 for sample in samples), f"clipped audio: {path.name}")
    peak = max(abs(sample) for sample in samples) / 32768
    rms = math.sqrt(sum(sample * sample for sample in samples) / count) / 32768
    require(peak > 0, f"silent audio: {path.name}")
    for name, actual in (("duration_seconds", count / 48000), ("peak", peak), ("rms", rms)):
        declared = artifact.get(name)
        require(isinstance(declared, (int, float)) and not isinstance(declared, bool)
                and math.isfinite(declared) and math.isclose(declared, actual, abs_tol=1e-6),
                f"audio metadata mismatch: {path.name} {name}")


def validate(root: Path = PACKAGE, *, manifest: dict | None = None,
             approvals: dict | None = None, require_approved: bool = False) -> dict:
    manifest = manifest if manifest is not None else json.loads((root / "package.json").read_text())
    approvals = approvals if approvals is not None else json.loads((root / "approvals.json").read_text())
    require(manifest.get("schema_version") == approvals.get("schema_version") == 1, "unsupported schema")
    ids = [entry["id"] for entry in manifest["selected_characters"]]
    require(len(ids) == 5 and set(ids) == set(CHARACTERS), "expected exactly the five selected character IDs")
    require(approvals["adoption_scope"].get("status") == "confirmed"
            and len(approvals["adoption_scope"]["ids"]) == 5
            and set(approvals["adoption_scope"]["ids"]) == set(CHARACTERS), "adoption scope differs")
    require(approvals["contract"].get("status") == "confirmed_complete"
            and nonempty(approvals["contract"].get("evidence"))
            and approvals["contract"].get("private_documents_included") is False, "contract record incomplete")
    require(manifest.get("release_enabled") is False, "this review package must keep release disabled")
    expected_counts = {"character_sheets": 10, "character_frames": 90, "keepsake_sheets": 5,
                       "keepsake_frames": 60, "audio_candidates": 11, "audio_selections": 5,
                       "content_descriptions": 10}
    require(manifest.get("production_deliverables") == expected_counts, "production counts differ from approved scope")
    artifacts, candidates, final_keys = {}, set(), set()
    for artifact in manifest["artifacts"]:
        relative = artifact["path"]
        path = safe_path(root, relative)
        require(relative not in artifacts, f"duplicate artifact path: {relative}")
        candidate = artifact.get("candidate_id")
        require(nonempty(candidate) and candidate not in candidates, "candidate IDs must be unique and nonempty")
        require(nonempty(artifact.get("license")), f"missing license: {relative}")
        require(artifact.get("role") in ROLES, f"unknown artifact role: {relative}")
        require(re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256"))) is not None
                and hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"], f"hash mismatch: {relative}")
        role = artifact["role"]
        if role in FINAL_ROLES:
            require(artifact.get("character_id") in CHARACTERS, f"unknown final character: {relative}")
            qualifier = None
            if role == "character_sheet":
                qualifier = artifact.get("sheet")
                require(qualifier in FRAME_NAMES, "character_sheet.sheet must be base or throw_hit")
            if role == "audio_candidate":
                qualifier = artifact.get("variant")
                require(qualifier in AUDIO_VARIANTS[artifact["character_id"]], "audio_candidate.variant differs from current review options")
            key = (role, artifact["character_id"], qualifier)
            require(key not in final_keys, f"duplicate final artifact role: {key}")
            final_keys.add(key)
        if role == "content_copy":
            require(path.suffix == ".json", "content copy must be JSON")
            copy = json.loads(path.read_text())
            require(copy.get("language") == "ko" and copy.get("character_id") == artifact["character_id"],
                    "content copy language/character mismatch")
            for subject in ("character", "keepsake"):
                require(isinstance(copy.get(subject), dict)
                        and all(nonempty(copy[subject].get(field)) for field in ("name", "description")),
                        f"content copy needs name and unique description: {subject}")
            require(nonempty(copy["keepsake"].get("id")), "content copy needs keepsake ID")
        elif role in ("audio_candidate", "audio_reference", "audio_archive"):
            validate_audio(path, artifact)
        else:
            require(path.suffix.lower() == ".png", f"image artifacts must be PNG: {relative}")
            require(png_dimensions(path) == artifact.get("dimensions"), f"dimensions mismatch: {relative}")
            validate_pixels(path, artifact)
        artifacts[relative] = artifact
        candidates.add(candidate)
    media = {path.relative_to(root).as_posix() for path in root.rglob("*")
             if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES}
    declared_media = {path for path, artifact in artifacts.items() if artifact["role"] != "content_copy"}
    require(media == declared_media, f"unlisted/missing media: {sorted(media ^ declared_media)}")
    expected_originals = {f"originals/{character}/{sheet}.png" for character in CHARACTERS for sheet in FRAME_NAMES}
    require({path for path, artifact in artifacts.items() if artifact["role"] == "original_sheet"}
            == expected_originals, "expected exactly ten original PNGs")
    source = json.loads((root / "source-audit.json").read_text())
    require(len(source["sheets"]) == 10 and {sheet["path"] for sheet in source["sheets"]} == expected_originals,
            "source audit sheet set differs")
    for sheet in source["sheets"]:
        artifact = artifacts[sheet["path"]]
        require(sheet["file_sha256"] == artifact["sha256"] and sheet["dimensions"] == artifact["dimensions"],
                f"original pin differs from source audit: {sheet['path']}")
        width, height, rgba = parse_rgba_png(root / sheet["path"])
        names = FRAME_NAMES[Path(sheet["path"]).stem]
        expected = [{"index": index, "state": name, **analyze_frame(frame_bytes(rgba, width, index))}
                    for index, name in enumerate(names)]
        require(sheet["frames"] == expected, f"source frame audit differs: {sheet['path']}")
    records = {}
    for record in approvals["records"]:
        key = (record.get("stage"), record.get("character_id"))
        require(key in EXPECTED_RECORDS and key not in records, f"unknown/duplicate approval: {key}")
        require(record.get("status") in ("pending", "approved"), f"unknown approval status: {key}")
        records[key] = record
        refs = record.get("artifacts")
        require(isinstance(refs, list), f"approval artifacts must be a list: {key}")
        referenced = set()
        for ref in refs:
            artifact = artifacts.get(ref.get("path"))
            require(artifact is not None and all(ref.get(field) == artifact[field]
                    for field in ("sha256", "candidate_id")), f"stale approval reference: {key}")
            require(artifact["path"] not in referenced, f"duplicate approval reference: {key}")
            referenced.add(artifact["path"])
        if record["status"] == "pending":
            require(record.get("selection") is None and record.get("user_evidence") is None,
                    f"pending record must not imply a selection or approval: {key}")
            continue
        require(nonempty(record.get("user_evidence")) and record["user_evidence"].strip().lower()
                not in {"pending", "todo", "tbd", "true", "approved", "승인", "승인됨", "없음"},
                f"actual nonempty user decision evidence required: {key}")
        require(refs, f"approved record needs pinned artifacts: {key}")
        selection = record.get("selection")
        selections = selection if isinstance(selection, list) else [selection]
        require(bool(selections) and all(nonempty(value) for value in selections)
                and len(set(selections)) == len(selections), f"approved record needs a selection: {key}")
        require("options" not in record or record["stage"] in
                ("appearance_direction", "keepsake_plan", "idle_timing"),
                f"final approvals must select actual candidate IDs: {key}")
        allowed = record.get("options", [ref["candidate_id"] for ref in refs])
        require(all(value in allowed for value in selections), f"selection not among referenced candidates/options: {key}")
        if record["stage"] in ("keepsake_plan", "idle_timing", "audio"):
            require(nonempty(selection), f"stage requires one selected option ID: {key}")
        referenced_artifacts = [artifacts[ref["path"]] for ref in refs]
        stage, character = key
        wanted = {
            "appearance_pixels": {("appearance_pose", None)},
            "character_frames": {("character_sheet", "base"), ("character_sheet", "throw_hit")},
            "character_motion": {("character_sheet", "base"), ("character_sheet", "throw_hit")},
            "keepsake_visual": {("keepsake_sheet", None)},
            "descriptions": {("content_copy", None)},
        }.get(stage)
        if wanted:
            available = {(item["role"], item.get("sheet")) for item in referenced_artifacts
                         if item.get("character_id") == character}
            require(wanted <= available, f"approval missing relevant final artifacts: {key}")
            required_candidates = {item["candidate_id"] for item in referenced_artifacts
                                   if item.get("character_id") == character
                                   and (item["role"], item.get("sheet")) in wanted}
            require(set(selections) == required_candidates,
                    f"approval selection must exactly identify required final candidates: {key}")
        if stage == "audio":
            require(any(item["role"] == "audio_candidate" and item.get("character_id") == character
                        and item["candidate_id"] == selection for item in referenced_artifacts),
                    f"audio selection must identify the chosen current WAV candidate: {key}")
        if stage == "composite":
            available = {item["role"] for item in referenced_artifacts if item.get("character_id") == character}
            require({"base", "throw_hit"} <= {item.get("sheet") for item in referenced_artifacts
                    if item["role"] == "character_sheet" and item.get("character_id") == character},
                    f"composite must pin both character sheets: {key}")
            require({"character_sheet", "keepsake_sheet", "audio_candidate"} <= available,
                    f"composite must pin character, keepsake and selected audio: {key}")
    require(set(records) == EXPECTED_RECORDS, "missing approval records")
    for artifact in artifacts.values():
        if artifact["role"] in ("keepsake_sheet", "audio_candidate"):
            plan = records[("keepsake_plan", artifact["character_id"])]
            require(artifact.get("keepsake_id") == plan["selection"],
                    "keepsake image/audio differs from selected plan")
        if artifact["role"] == "content_copy":
            copy = json.loads((root / artifact["path"]).read_text())
            plan = records[("keepsake_plan", artifact["character_id"])]
            require(copy["keepsake"]["id"] == plan["selection"], "content copy keepsake differs from selected plan")
    concept = approvals.get("concept_art_approval")
    if concept is not None:
        require(concept.get("status") == "approved_for_selected_concepts"
                and nonempty(concept.get("user_evidence")) and nonempty(concept.get("scope")),
                "concept approval requires status, user evidence and limited scope")
        items = concept.get("items")
        selected_items = {record["selection"] for (stage, _), record in records.items()
                          if stage == "keepsake_plan" and record["status"] == "approved"}
        require(isinstance(items, list) and items and all(nonempty(item) for item in items)
                and len(set(items)) == len(items) and set(items) <= selected_items,
                "concept approval items must match selected keepsake plans")
        refs = concept.get("artifacts")
        require(isinstance(refs, list) and refs, "concept approval requires pinned artifacts")
        referenced = set()
        for ref in refs:
            artifact = artifacts.get(ref.get("path"))
            require(artifact is not None and artifact["role"] == "concept_board"
                    and all(ref.get(field) == artifact[field] for field in ("sha256", "candidate_id")),
                    "stale concept approval reference")
            require(artifact["path"] not in referenced, "duplicate concept approval reference")
            referenced.add(artifact["path"])
    for (stage, character), record in records.items():
        if record["status"] != "approved":
            continue
        for earlier in PREDECESSORS.get(stage, ()):
            predecessor = records[(earlier, "all" if earlier == "appearance_direction" else character)]
            require(predecessor["status"] == "approved", f"approval order violation: {stage}/{character} before {earlier}")
        if stage == "composite":
            selected_audio = records[("audio", character)]["selection"]
            require(selected_audio in {ref["candidate_id"] for ref in record["artifacts"]},
                    f"composite does not pin the approved audio: {character}")
            referenced_artifacts = [artifacts[ref["path"]] for ref in record["artifacts"]]
            required_candidates = {item["candidate_id"] for item in referenced_artifacts
                                   if item.get("character_id") == character
                                   and item["role"] in ("character_sheet", "keepsake_sheet")}
            required_candidates.add(selected_audio)
            selection = record["selection"]
            selections = selection if isinstance(selection, list) else [selection]
            require(set(selections) == required_candidates,
                    f"composite selection must exactly identify both character sheets, keepsake and approved audio: {character}")
    missing = []
    for character in CHARACTERS:
        expected = {("appearance_pose", character, None), ("keepsake_sheet", character, None),
                    ("content_copy", character, None)}
        expected |= {("character_sheet", character, sheet) for sheet in FRAME_NAMES}
        expected |= {("audio_candidate", character, variant) for variant in AUDIO_VARIANTS[character]}
        missing.extend(sorted(expected - final_keys))
    pending = [f"{stage}/{character}" for (stage, character), record in records.items() if record["status"] != "approved"]
    if require_approved:
        require(not pending and not missing,
                f"not approved: {len(pending)} pending stages; {len(missing)} missing final artifacts")
    return {"artifacts": len(artifacts), "pending_stages": len(pending), "missing_final_artifacts": len(missing),
            "ready": not pending and not missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(require_approved=args.require_approved)
    except (ValueError, AssertionError, KeyError, TypeError, OSError, wave.Error, struct.error) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {result['artifacts']} artifacts; {result['pending_stages']} pending approval stages; "
          f"{result['missing_final_artifacts']} missing final artifacts")
    print("Review-package integrity only. User approval and final deliverables are separate; release stays disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
