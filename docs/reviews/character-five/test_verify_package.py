#!/usr/bin/env python3
"""Approval integrity and production rejection tests; no package files are written."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import wave
import zlib

sys.dont_write_bytecode = True
from verify_package import PACKAGE, safe_path, validate, validate_audio, validate_pixels


class PackageApprovalTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((PACKAGE / "package.json").read_text())
        self.approvals = json.loads((PACKAGE / "approvals.json").read_text())
        # Exercise pending-approval rejection independently of real approval progress.
        for record in self.approvals["records"]:
            if record["stage"] not in ("appearance_direction", "keepsake_plan"):
                record.update(status="pending", selection=None, user_evidence=None)

    def test_real_package_has_all_final_approvals(self):
        self.assertTrue(validate(require_approved=True)["ready"])

    def direction(self):
        record = next(record for record in self.approvals["records"] if record["stage"] == "appearance_direction")
        board = next(item for item in self.manifest["artifacts"] if item["role"] == "concept_board")
        record["artifacts"] = [{key: board[key] for key in ("path", "sha256", "candidate_id")}]
        record["status"] = "approved"
        record["selection"] = record["artifacts"][0]["candidate_id"]
        record.pop("options", None)
        record["user_evidence"] = "TEST FIXTURE ONLY: user chose this pinned direction board."
        return record

    def run_validation(self, root=PACKAGE, **options):
        return validate(root, manifest=self.manifest, approvals=self.approvals, **options)

    def test_current_package_integrity_does_not_claim_readiness(self):
        result = self.run_validation()
        self.assertFalse(result["ready"])
        self.assertGreater(result["pending_stages"], 0)
        with self.assertRaisesRegex(ValueError, "not approved"):
            self.run_validation(require_approved=True)

    def test_complete_approval_fixture_selects_exact_assets_audio_and_copy(self):
        # This in-memory fixture never writes an approval into the package.
        for record in self.approvals["records"]:
            if record["status"] == "approved":
                continue
            stage = record["stage"]
            refs = [item for item in self.manifest["artifacts"]
                    if item["path"] in {ref["path"] for ref in record["artifacts"]}]
            if stage == "idle_timing":
                selection = record["options"][0]
            elif stage == "audio":
                selection = next(item["candidate_id"] for item in refs if item["role"] == "audio_candidate")
            elif stage == "composite":
                chosen = next(item["candidate_id"] for item in refs if item["role"] == "audio_candidate")
                selection = [item["candidate_id"] for item in refs
                             if item["role"] != "audio_candidate" or item["candidate_id"] == chosen]
            else:
                selection = [item["candidate_id"] for item in refs]
            record.update(status="approved", selection=selection,
                          user_evidence="TEST FIXTURE ONLY: explicitly selected these pinned candidates.")
        self.assertTrue(self.run_validation(require_approved=True)["ready"])

    def test_approved_direction_is_bound_to_current_board(self):
        self.direction()
        result = self.run_validation()
        self.assertFalse(result["ready"])

    def test_changed_file_and_updated_manifest_invalidate_old_approval(self):
        record = self.direction()
        with tempfile.TemporaryDirectory(prefix="sidey-approval-test-") as temporary:
            root = Path(temporary)
            for item in self.manifest["artifacts"]:
                target = root / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(PACKAGE / item["path"], target)
            shutil.copyfile(PACKAGE / "source-audit.json", root / "source-audit.json")
            relative = record["artifacts"][0]["path"]
            path = root / relative
            before = path.read_bytes()
            payload = b"review-test\x00changed file bytes"
            kind = b"tEXt"
            chunk = struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
            path.write_bytes(before[:-12] + chunk + before[-12:])
            artifact = next(item for item in self.manifest["artifacts"] if item["path"] == relative)
            artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "stale approval reference"):
                self.run_validation(root)
        self.assertEqual(hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest(),
                         record["artifacts"][0]["sha256"])

    def test_hash_mismatch_cannot_be_approved(self):
        self.manifest["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_validation()

    def test_audio_reference_cannot_fill_a_missing_candidate(self):
        candidate = next(item for item in self.manifest["artifacts"]
                         if item["role"] == "audio_candidate" and item["character_id"] == "pixel_poop")
        candidate["role"] = "audio_reference"
        result = self.run_validation()
        self.assertEqual(result["missing_final_artifacts"], 1)
        self.assertFalse(result["ready"])

    def test_keepsake_and_audio_must_match_the_character_selected_item(self):
        original = copy.deepcopy(self.manifest)
        for role in ("keepsake_sheet", "audio_candidate"):
            with self.subTest(role=role):
                self.manifest = copy.deepcopy(original)
                item = next(item for item in self.manifest["artifacts"]
                            if item["role"] == role and item["character_id"] == "pixel_shiba")
                item["keepsake_id"] = "rubber_duck"
                with self.assertRaisesRegex(ValueError, "differs from selected plan"):
                    self.run_validation()

    def test_description_approval_is_bound_to_exact_character_copy(self):
        record = next(record for record in self.approvals["records"] if record["stage"] == "descriptions")
        other = next(item for item in self.manifest["artifacts"] if item["role"] == "content_copy"
                     and item["character_id"] != record["character_id"])
        record.update(status="approved", selection=other["candidate_id"],
                      user_evidence="TEST FIXTURE: wrong character description selected",
                      artifacts=[{key: other[key] for key in ("path", "sha256", "candidate_id")}])
        with self.assertRaisesRegex(ValueError, "missing relevant final artifacts"):
            self.run_validation()

    def test_description_and_audio_references_reject_stale_hashes(self):
        original = copy.deepcopy(self.approvals)
        for stage in ("descriptions", "audio"):
            with self.subTest(stage=stage):
                self.approvals = copy.deepcopy(original)
                record = next(record for record in self.approvals["records"] if record["stage"] == stage)
                record["artifacts"][0]["sha256"] = "0" * 64
                with self.assertRaisesRegex(ValueError, "stale approval reference"):
                    self.run_validation()

    def test_pending_selection_is_not_approval(self):
        record = next(record for record in self.approvals["records"] if record["status"] == "pending")
        record["selection"] = "looks_good"
        with self.assertRaisesRegex(ValueError, "pending record"):
            self.run_validation()

    def test_approval_requires_actual_evidence(self):
        record = self.direction()
        record["user_evidence"] = "approved"
        with self.assertRaisesRegex(ValueError, "user decision evidence"):
            self.run_validation()

    def test_unknown_duplicate_or_missing_stage_rejected(self):
        original = copy.deepcopy(self.approvals)
        for mutation in ("duplicate", "unknown", "missing"):
            with self.subTest(mutation=mutation):
                self.approvals = copy.deepcopy(original)
                if mutation == "duplicate":
                    self.approvals["records"].append(copy.deepcopy(self.approvals["records"][0]))
                elif mutation == "unknown":
                    self.approvals["records"][0]["stage"] = "automatic_approval"
                else:
                    self.approvals["records"].pop()
                with self.assertRaisesRegex(ValueError, "approval"):
                    self.run_validation()

    def test_pixel_approval_requires_prior_direction_approval(self):
        direction = next(record for record in self.approvals["records"]
                         if record["stage"] == "appearance_direction")
        direction.update(status="pending", selection=None, user_evidence=None)
        artifact = next(item for item in self.manifest["artifacts"]
                        if item["role"] == "appearance_pose" and item["character_id"] == "pixel_shiba")
        record = next(record for record in self.approvals["records"]
                      if record["stage"] == "appearance_pixels" and record["character_id"] == "pixel_shiba")
        record.update(status="approved", selection=artifact["candidate_id"],
                      user_evidence="TEST FIXTURE ONLY: user selected this 24px appearance.",
                      artifacts=[{key: artifact[key] for key in ("path", "sha256", "candidate_id")}])
        with self.assertRaisesRegex(ValueError, "approval order violation"):
            self.run_validation()

    def test_final_stage_cannot_approve_a_concept_board(self):
        board = next(item for item in self.manifest["artifacts"] if item["role"] == "concept_board")
        record = next(record for record in self.approvals["records"]
                      if record["stage"] == "character_frames" and record["character_id"] == "pixel_shiba")
        record.update(status="approved", selection=board["candidate_id"],
                      user_evidence="TEST FIXTURE ONLY: board was incorrectly labelled as final frames.",
                      artifacts=[{key: board[key] for key in ("path", "sha256", "candidate_id")}])
        with self.assertRaisesRegex(ValueError, "missing relevant final artifacts"):
            self.run_validation()

    def test_pixel_selection_cannot_be_a_board_with_correct_pose_only_in_evidence(self):
        pose = next(item for item in self.manifest["artifacts"]
                    if item["role"] == "appearance_pose" and item["character_id"] == "pixel_shiba")
        board = next(item for item in self.manifest["artifacts"] if item["role"] == "concept_board")
        other_pose = next(item for item in self.manifest["artifacts"]
                          if item["role"] == "appearance_pose" and item["character_id"] == "pixel_duck")
        record = next(record for record in self.approvals["records"]
                      if record["stage"] == "appearance_pixels" and record["character_id"] == "pixel_shiba")
        record.update(status="approved",
                      user_evidence="TEST FIXTURE ONLY: actual selection must match the character and final role.",
                      artifacts=[{key: item[key] for key in ("path", "sha256", "candidate_id")}
                                 for item in (pose, board, other_pose)])
        # Extra evidence references are allowed, but cannot replace or augment the selected final pose.
        for wrong in (board["candidate_id"], other_pose["candidate_id"],
                      [pose["candidate_id"], board["candidate_id"]]):
            with self.subTest(selection=wrong):
                record["selection"] = wrong
                with self.assertRaisesRegex(ValueError, "selection must exactly identify required final candidates"):
                    self.run_validation()
        record["selection"] = pose["candidate_id"]
        self.run_validation()

    def test_candidate_id_substitution_invalidates_reference(self):
        self.direction()["artifacts"][0]["candidate_id"] = "different-candidate"
        with self.assertRaisesRegex(ValueError, "stale approval reference"):
            self.run_validation()

    def test_concept_approval_rejects_stale_hash_and_candidate(self):
        original = copy.deepcopy(self.approvals)
        for field, wrong in (("sha256", "0" * 64), ("candidate_id", "different-concept")):
            with self.subTest(field=field):
                self.approvals = copy.deepcopy(original)
                self.approvals["concept_art_approval"]["artifacts"][0][field] = wrong
                with self.assertRaisesRegex(ValueError, "stale concept approval"):
                    self.run_validation()

    def test_concept_approval_requires_selected_items_and_evidence(self):
        original = copy.deepcopy(self.approvals)
        for field, wrong in (("items", ["grass_bundle"]), ("user_evidence", ""), ("artifacts", [])):
            with self.subTest(field=field):
                self.approvals = copy.deepcopy(original)
                self.approvals["concept_art_approval"][field] = wrong
                with self.assertRaisesRegex(ValueError, "concept approval"):
                    self.run_validation()

    def test_path_escape_rejected(self):
        for relative in ("../secret.png", "/tmp/secret.png", "originals/../secret.png", "C:\\secret.png"):
            with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, "unsafe"):
                safe_path(PACKAGE, relative)

    def test_unlisted_media_rejected(self):
        with tempfile.TemporaryDirectory(prefix="sidey-media-test-") as temporary:
            root = Path(temporary)
            for item in self.manifest["artifacts"]:
                target = root / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(PACKAGE / item["path"], target)
            (root / "unlisted.wav").write_bytes(b"unlisted")
            with self.assertRaisesRegex(ValueError, "unlisted/missing media"):
                self.run_validation(root)


class ProductionMediaTests(unittest.TestCase):
    def test_originals_cannot_be_relabelled_as_corrected_final_sheets(self):
        path = PACKAGE / "originals/pixel_shiba/base.png"
        with self.assertRaisesRegex(ValueError, "detached foot row"):
            validate_pixels(path, {"role": "character_sheet", "sheet": "base", "path": str(path)})

    def test_audio_metadata_and_format_gate(self):
        with tempfile.TemporaryDirectory(prefix="sidey-audio-test-") as temporary:
            path = Path(temporary) / "candidate.wav"
            samples = (0, 4096, -4096, 0)
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(struct.pack("<4h", *samples))
            metadata = {"source": "Synthetic test fixture", "duration_seconds": 4 / 48000,
                        "peak": 0.125, "rms": (0.125 ** 2 / 2) ** 0.5}
            validate_audio(path, metadata)
            for key, replacement in (("rms", float("nan")), ("peak", 1), ("duration_seconds", 1), ("source", "")):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    validate_audio(path, {**metadata, key: replacement})
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(struct.pack("<h", 32767))
            with self.assertRaisesRegex(ValueError, "clipped"):
                validate_audio(path, metadata)
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(44100)
                output.writeframes(struct.pack("<h", 1))
            with self.assertRaisesRegex(ValueError, "48kHz"):
                validate_audio(path, metadata)


if __name__ == "__main__":
    unittest.main()
