#!/usr/bin/env python3
"""Recorded Foley revisions: three light ball pops, three wet slaps, exact duck.

Read-only verification by default; --write changes only this revision's review
WAVs and metadata. Existing audio-v1 and all active/source assets stay intact.
"""
from __future__ import annotations

import argparse
import cmath
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import wave

sys.dont_write_bytecode = True
from build_audio import RATE, ROOT, REPOSITORY, decode, metrics

LICENSE = "SIDEY Paid Asset License 1.0 (package scope: LICENSE.md); underlying recorded Foley CC0-1.0 remains CC0"
FEEDBACK = REPOSITORY / "docs/reviews/character-feedback"
DUCK_SHA = "805048802a0494d51c453000c3bc624f8713c23f9c5c5530dafc68be683715af"
PORK_SHA = "fad893141f5648315a6c9cfa72d618a238d1230ce6c87b7eb0733f634663949f"
SPECS = {
    "tennis_ball": [
        {"variant": "1", "label": "톡 · 작고 말랑한 한 번의 팝", "source_id": "mouth-573153", "speed": 1.20,
         "duration": .105, "highpass_hz": 180, "lowpass_hz": 4800, "layer": None},
        {"variant": "2", "label": "뽕 · 둥글고 가벼운 입술 팝", "source_id": "mouth-258269", "speed": 1.32,
         "duration": .12, "highpass_hz": 230, "lowpass_hz": 4000, "layer": None},
        {"variant": "3", "label": "뽁 · 빠르고 통통한 작은 팝", "source_id": "mouth-691906", "speed": 1.08,
         "duration": .10, "highpass_hz": 210, "lowpass_hz": 5400, "layer": None},
    ],
    "fish_cake_skewer": [
        {"variant": "1", "label": "췁 · 짧고 촉촉한 한 대", "source_id": "approved-pork-wet-slap", "speed": 1.20,
         "duration": .15, "highpass_hz": 420, "lowpass_hz": 6800, "layer": None},
        {"variant": "2", "label": "촥 · 얇게 달라붙는 빠른 타격", "source_id": "approved-pork-wet-slap", "speed": 1.43,
         "duration": .13, "highpass_hz": 700, "lowpass_hz": 7600,
         "layer": {"source_id": "mouth-691906", "speed": 1.25, "offset_seconds": .022, "gain": .16}},
        {"variant": "3", "label": "췁췁 · 한 충돌 안에서 찰지게 겹치는 타격", "source_id": "approved-pork-wet-slap", "speed": 1.03,
         "duration": .19, "highpass_hz": 550, "lowpass_hz": 6200,
         "layer": {"source_id": "approved-pork-wet-slap", "speed": 1.20, "offset_seconds": .036, "gain": .48}},
    ],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_records():
    entries = {}
    for item in json.loads((FEEDBACK / "round-6/sources/manifest.json").read_text())["sources"]:
        path = FEEDBACK / "round-6/sources" / item["decoded_file"]
        if sha(path.read_bytes()) != item["decoded_sha256"]:
            raise ValueError(f"changed original Foley: {path.name}")
        entries[item["id"]] = {"path": path.relative_to(REPOSITORY).as_posix(), "sha256": item["decoded_sha256"],
                                "author": item["author"], "license": item["license"],
                                "page_url": item["page_url"], "source_record": item}
    path = REPOSITORY / "assets/v1/audio/impact-pork.wav"
    assert sha(path.read_bytes()) == PORK_SHA
    license_record = next(item for item in json.loads((REPOSITORY / "assets/v1/audio/source-licenses.json").read_text())["sources"]
                          if item["id"] == "wet-slap-570787")
    approval = next(item for item in json.loads((REPOSITORY / "assets/v1/audio/approval.json").read_text())["sounds"]
                    if item["object_id"] == "pork")
    assert approval["sha256"] == PORK_SHA
    entries["approved-pork-wet-slap"] = {"path": path.relative_to(REPOSITORY).as_posix(), "sha256": PORK_SHA,
                                          "author": license_record["author"], "license": "CC0-1.0 source; SIDEY edited asset",
                                          "page_url": license_record["page_url"], "source_record": license_record,
                                          "prior_processing": approval["source"],
                                          "note": "기존 승인된 돼지고기 소리의 젖은 slap Foley를 재편집; 실제 어묵 녹음으로 주장하지 않음"}
    return entries


def lowpass(values, cutoff, stages=2):
    result = list(values)
    alpha = 1 - math.exp(-2 * math.pi * cutoff / RATE)
    for _ in range(stages):
        state = 0.0
        for i, value in enumerate(result):
            state += alpha * (value - state)
            result[i] = state
    return result


def highpass(values, cutoff, stages=2):
    result = list(values)
    alpha = 1 - math.exp(-2 * math.pi * cutoff / RATE)
    for _ in range(stages):
        state = 0.0
        for i, value in enumerate(result):
            state += alpha * (value - state)
            result[i] = value - state
    return result


def trim_source(source_id, records):
    raw, _ = decode((REPOSITORY / records[source_id]["path"]).read_bytes())
    values = [value / 32768 for value in raw]
    peak = max(map(abs, values))
    # Remove the wet recording's quiet lead so the slap lands at contact.
    threshold = .16 if source_id == "approved-pork-wet-slap" else .03
    first = next(i for i, value in enumerate(values) if abs(value) >= peak * threshold)
    last = len(values) - next(i for i, value in enumerate(reversed(values)) if abs(value) >= peak * .015)
    first = max(0, first - 48)
    last = min(len(values), last + 240)
    return values[first:last], {"start_seconds": first / RATE, "end_seconds": last / RATE,
                               "threshold_of_source_peak": threshold}


def resample(values, speed):
    # Recorded texture with linear time/pitch scaling; never adds oscillators.
    values = lowpass(values, 8500)
    result = []
    for i in range(int((len(values) - 1) / speed)):
        position = i * speed
        index = int(position)
        fraction = position - index
        result.append(values[index] * (1 - fraction) + values[index + 1] * fraction)
    return result


def normalize(values, target_rms):
    mean = sum(values) / len(values)
    values = [(value - mean) * min(1, i / (RATE * .001))
              * min(1, (len(values) - 1 - i) / (RATE * .012)) for i, value in enumerate(values)]
    peak = max(map(abs, values))
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    # Linear gain preserves the recorded wet transient; no compression/saturation.
    gain = min(target_rms / rms, .27 / peak)
    samples = [round(value * gain * 32768) for value in values]
    assert samples[0] == samples[-1] == 0 and all(-32768 < value < 32767 for value in samples)
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(RATE)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return stream.getvalue(), gain


def spectrum(data):
    """Radix-2 FFT energy bands of decoded PCM, for texture comparison only."""
    samples, count = decode(data)
    size = 1 << (count - 1).bit_length()
    values = [complex(value / 32768, 0) for value in samples] + [0j] * (size - count)
    j = 0
    for i in range(1, size):
        bit = size >> 1
        while j & bit:
            j ^= bit; bit >>= 1
        j ^= bit
        if i < j: values[i], values[j] = values[j], values[i]
    width = 2
    while width <= size:
        step = cmath.exp(-2j * math.pi / width)
        for start in range(0, size, width):
            phase = 1 + 0j
            for offset in range(width // 2):
                even = values[start + offset]
                odd = phase * values[start + offset + width // 2]
                values[start + offset] = even + odd
                values[start + offset + width // 2] = even - odd
                phase *= step
        width *= 2
    energies = [abs(value) ** 2 for value in values[:size // 2 + 1]]
    total = sum(energies)
    return {"method": "zero-padded PCM FFT, positive-frequency energy fractions; not perceived loudness",
            "below_350hz_energy_fraction": sum(e for i, e in enumerate(energies) if i * RATE / size < 350) / total,
            "above_6000hz_energy_fraction": sum(e for i, e in enumerate(energies) if i * RATE / size > 6000) / total,
            "spectral_centroid_hz": sum(i * RATE / size * e for i, e in enumerate(energies)) / total}


def build():
    records = source_records()
    reference = metrics((ROOT / "references/impact-baseball.wav").read_bytes())
    comparison_data = (FEEDBACK / "round-7/audio/throwable_squeaky_duck-b-v5.wav").read_bytes()
    assert sha(comparison_data) == DUCK_SHA
    comparison = metrics(comparison_data)
    outputs, artifacts = {}, []
    for keepsake, specs in SPECS.items():
        for spec in specs:
            source, trim = trim_source(spec["source_id"], records)
            main = resample(source, spec["speed"])
            values = [0.0] * round(spec["duration"] * RATE)
            for i, value in enumerate(main[:len(values)]): values[i] += value
            processing = {"main_trim": trim, "parameters": spec,
                          "gain_method": "linear RMS match to unchanged approved duck, constrained by peak 0.27; recorded transients are not compressed"}
            source_ids = [spec["source_id"]]
            if spec["layer"]:
                layer = spec["layer"]
                raw, layer_trim = trim_source(layer["source_id"], records)
                extra = resample(raw, layer["speed"])
                # Normalize layer relative to the main attack before layering.
                gain = layer["gain"] * max(map(abs, main)) / max(map(abs, extra))
                start = round(layer["offset_seconds"] * RATE)
                for i, value in enumerate(extra[:len(values) - start]): values[start + i] += value * gain
                processing["secondary_trim"] = layer_trim
                source_ids.append(layer["source_id"])
            values = lowpass(highpass(values, spec["highpass_hz"]), spec["lowpass_hz"])
            data, gain = normalize(values, comparison["rms"])
            processing["final_linear_gain"] = gain
            measured = metrics(data)
            spectral = spectrum(data)
            assert measured["clipped_samples"] == 0
            assert measured["peak"] <= .27 + 1 / 32768
            if keepsake == "fish_cake_skewer":
                assert spectral["below_350hz_energy_fraction"] < .10, "wet slap must not regain low drum resonance"
            path = ROOT / f"candidates/audio-v2/{keepsake}/{spec['variant']}.wav"
            outputs[path] = data
            artifacts.append({"role": "audio_candidate", "character_id": "pixel_shiba" if keepsake == "tennis_ball" else "pixel_tteokbokki",
                              "keepsake_id": keepsake, "variant": spec["variant"], "candidate_id": f"audio-v2-{keepsake}-{spec['variant']}",
                              "path": path.relative_to(ROOT).as_posix(), "sha256": sha(data), "label": spec["label"],
                              "source": "Recorded CC0 Foley from pinned local repository sources; crop/resample/filter/layer and linear gain only; no synthesized sine/drum/launch/flight layer",
                              "source_ids": sorted(set(source_ids)), "license": LICENSE, "processing": processing,
                              "approval_status": "pending_user_audio_and_composite_approval", **measured, "spectrum": spectral,
                              "reference_peak_delta_db": measured["peak_dbfs"] - reference["peak_dbfs"],
                              "reference_rms_delta_db": measured["rms_dbfs"] - reference["rms_dbfs"],
                              "unchanged_duck_rms_delta_db": measured["rms_dbfs"] - comparison["rms_dbfs"]})

    approval = json.loads((FEEDBACK / "audio-approval.json").read_text())
    selected = next(item for item in approval["sounds"] if item["object_id"] == "throwable_squeaky_duck")
    data = (FEEDBACK / selected["file"]).read_bytes()
    assert selected["candidate_id"] == "throwable_squeaky_duck-b-v5" and selected["sha256"] == sha(data) == DUCK_SHA
    # Read-only provenance check against the actual macOS object -> WAV mapping.
    runtime = REPOSITORY / "macos/SIDEY/Resources/DirectImpactAudio/impact-throwable_squeaky_duck.wav"
    assert runtime.read_bytes() == data
    path = ROOT / "candidates/audio-v2/rubber_duck/original.wav"
    outputs[path] = data
    duck_source = next(item for item in json.loads((FEEDBACK / "round-4/sources/manifest.json").read_text())["sources"] if item["id"] == "duck")
    artifacts.append({"role": "audio_candidate", "character_id": "pixel_duck", "keepsake_id": "rubber_duck",
                      "variant": "original", "candidate_id": "audio-v2-rubber_duck-original", "path": path.relative_to(ROOT).as_posix(),
                      "sha256": DUCK_SHA, "label": "기존 삑삑 오리 · 꽥 한 번", "license": LICENSE,
                      "source": "기존 승인 throwable_squeaky_duck-b-v5 WAV와 macOS 실제 리소스의 바이트 동일 복사. 신규 삑 합성·리샘플·음량 변경 없음",
                      "source_path": (FEEDBACK / selected["file"]).relative_to(REPOSITORY).as_posix(), "source_sha256": DUCK_SHA,
                      "source_record": duck_source, "original_approval_record": "docs/reviews/character-feedback/audio-approval.json",
                      "runtime_resource": runtime.relative_to(REPOSITORY).as_posix(),
                      "runtime_mapping": "macos/SIDEY/Features/PixelWorld/CharacterImpactAudio.swift: objectIDs + impact-<id>.wav bundle lookup",
                      "prior_processing": "round-5/generate_audio.py duck variant B: one contiguous recorded quack, playback rate 1.15, linear gain and fades; then unchanged through round-7",
                      "approval_status": "existing_approved_sound_reuse_requested", **metrics(data)})
    assert len({item["sha256"] for item in artifacts}) == 7
    comparison = {}
    for keepsake in SPECS:
        comparison[keepsake] = {variant: spectrum((ROOT / f"candidates/audio-v1/{keepsake}/{variant}.wav").read_bytes()) for variant in ("A", "B")}
    report = {"schema_version": 1, "candidate_version": "audio-v2", "generator": "build_audio_v2.py",
              "generator_sha256": sha(Path(__file__).read_bytes()), "sources": records, "artifacts": artifacts,
              "changes": ["어묵의 v1 저역 사인파 몸통을 완전히 제거하고 기존 승인된 CC0 wet-slap 녹음으로 교체",
                          "테니스공은 사인파 공명 대신 서로 다른 실제 입술 pop 녹음 3종을 짧게 편집; 전자음·멜로디 없음",
                          "오리는 이전 합성 A/B를 채택하지 않고 기존 상품의 승인된 꽥 WAV를 바이트 그대로 재사용",
                          "휴지·잎사귀 음원은 변경하지 않으며 기존 audio-v1 파일을 계속 사용"],
              "qa": {"method": "decoded PCM format/level/edge checks, source hashes, exact regeneration, FFT energy-band comparison",
                     "human_listening_performed": False, "prior_v1_spectrum": comparison,
                     "level_target": "기존 승인 오리 WAV의 RMS -29.44dBFS에 맞추되 녹음 transient를 보존하도록 peak 0.27로 제한. 이전 야구공 기준 대비 차이도 개별 파일에 그대로 기록",
                     "limitation": "녹음 기반 질감과 저역 감소를 수치로 확인했으나 귀여움·찰진 정도의 청감 승인은 사용자 재생 선택이 필요함"}}
    outputs[ROOT / "audio-v2-review.json"] = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    for path, data in build().items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        elif not path.is_file() or path.read_bytes() != data:
            print(f"FAIL: stale/missing {path.relative_to(ROOT)}"); return 1
    print(f"{'WROTE' if args.write else 'PASS'}: six recorded Foley candidates + exact previously approved duck WAV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
