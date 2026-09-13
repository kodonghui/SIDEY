#!/usr/bin/env python3
"""Review-only paper/leaf friction Foley. Default verifies; --write regenerates.

Uses two pinned CC0 recordings; does not synthesize impact, oscillator, launch,
or flight sounds. Decoded source WAVs are pinned for portable stdlib replay.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import wave

sys.dont_write_bytecode = True
from build_audio import ROOT, RATE, decode, metrics
from build_audio_v2 import highpass, lowpass, spectrum

LICENSE = "SIDEY Paid Asset License 1.0 (package scope: LICENSE.md); underlying recorded Foley CC0-1.0 remains CC0"
SOURCES = {
    "paper-632220": {
        "author": "golovlev.sound", "title": "paper, thin, tracing, blueprint, rustle.wav",
        "page_url": "https://freesound.org/people/golovlev.sound/sounds/632220/",
        "download_url": "https://cdn.freesound.org/previews/632/632220_3784464-hq.mp3",
        "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "license_verified_on": "2026-09-13", "page_description": "얇은 종이를 움직이는 마찰 녹음; 휴지 자체의 녹음이라고 주장하지 않음",
        "mp3_sha256": "3cb1538043c32ebd9a1b437aa2e79e899cda594a41552ba03b62e144ee6673e2",
        "wav_sha256": "50941ab820073d0eeeeb15760f35ed12ce54c2c9623d07f420f44ce737124d20",
    },
    "leaf-106131": {
        "author": "j1987", "title": "leafrustle.wav",
        "page_url": "https://freesound.org/people/j1987/sounds/106131/",
        "download_url": "https://cdn.freesound.org/previews/106/106131_367313-hq.mp3",
        "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "license_verified_on": "2026-09-13", "page_description": "작은 잎더미를 뒤적이는 실제 녹음",
        "mp3_sha256": "c0a5e079529db8cc6498612920b08ff16f173899edf5ae79391b15081569f2d1",
        "wav_sha256": "cf50dd444ad9de1169068f1eb30973cf52687095f777d370f7acc135d01cb5a5",
    },
}
SPECS = [
    {"keepsake_id": "tissue_ball", "character_id": "pixel_poop", "variant": "A", "source_id": "paper-632220",
     "label": "사락 · 얇은 종이가 가볍게 스치는 소리", "start_seconds": .48, "duration_seconds": .28,
     "highpass_hz": 550, "lowpass_hz": 5400},
    {"keepsake_id": "tissue_ball", "character_id": "pixel_poop", "variant": "B", "source_id": "paper-632220",
     "label": "사사삭 · 종이를 살짝 구기는 마찰", "start_seconds": 1.56, "duration_seconds": .32,
     "highpass_hz": 650, "lowpass_hz": 5000},
    {"keepsake_id": "leaf", "character_id": "pixel_quokka", "variant": "A", "source_id": "leaf-106131",
     "label": "사부작 · 잎이 부드럽게 서로 스치는 소리", "start_seconds": .44, "duration_seconds": .30,
     "highpass_hz": 600, "lowpass_hz": 4900},
    {"keepsake_id": "leaf", "character_id": "pixel_quokka", "variant": "B", "source_id": "leaf-106131",
     "label": "바스락 · 작은 잎을 가볍게 뒤적이는 소리", "start_seconds": .76, "duration_seconds": .28,
     "highpass_hz": 600, "lowpass_hz": 5400},
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(raw, spec):
    first, count = round(spec["start_seconds"] * RATE), round(spec["duration_seconds"] * RATE)
    assert first + count <= len(raw)
    values = [v / 32768 for v in raw[first:first + count]]
    values = lowpass(highpass(values, spec["highpass_hz"], stages=2), spec["lowpass_hz"], stages=2)
    mean = sum(values) / count
    # A gradual friction onset avoids the old pop/thud-shaped attack.
    values = [(v - mean) * min(1, i / (RATE * .020)) * min(1, (count - 1 - i) / (RATE * .050))
              for i, v in enumerate(values)]
    peak = max(map(abs, values))
    rms = math.sqrt(sum(v * v for v in values) / count)
    # Never force a quiet texture up to the old impact RMS. Max amplification
    # is 2.2×, peak is -20dBFS or lower, and RMS target is -34dBFS.
    gain = min(2.2, .020 / rms, .100 / peak)
    pcm = [round(v * gain * 32768) for v in values]
    assert pcm[0] == pcm[-1] == 0 and max(map(abs, pcm)) < 32767
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(RATE)
        wav.writeframes(struct.pack(f"<{count}h", *pcm))
    return buffer.getvalue(), gain


def build():
    outputs, artifacts, source_artifacts, decoded = {}, [], [], {}
    for key, source in SOURCES.items():
        for suffix in ("mp3", "wav"):
            path = ROOT / f"sources/audio-v3/{key}.{suffix}"
            assert path.is_file() and sha(path.read_bytes()) == source[f"{suffix}_sha256"], f"changed source {path.name}"
            source_artifacts.append({"role": "audio_source", "candidate_id": f"audio-v3-source-{key}-{suffix}",
                                     "path": path.relative_to(ROOT).as_posix(), "sha256": source[f"{suffix}_sha256"],
                                     "license": "CC0-1.0", "source": f"{source['author']} · {source['title']} · {source['page_url']}",
                                     "author": source["author"], "page_url": source["page_url"],
                                     "download_url": source["download_url"],
                                     "source_kind": "public HQ MP3 preview, not original master" if suffix == "mp3" else "decoded HQ preview, 48000Hz mono PCM16"})
        decoded[key], _ = decode((ROOT / f"sources/audio-v3/{key}.wav").read_bytes())
    for spec in SPECS:
        data, gain = render(decoded[spec["source_id"]], spec)
        measured, spectral = metrics(data), spectrum(data)
        assert measured["peak"] <= .100 + 1 / 32768 and measured["clipped_samples"] == 0
        assert spectral["below_350hz_energy_fraction"] < .04, "friction must not regain low impact body"
        old = metrics((ROOT / f"candidates/audio-v1/{spec['keepsake_id']}/{spec['variant']}.wav").read_bytes())
        assert measured["rms_dbfs"] < old["rms_dbfs"] - 5
        path = ROOT / f"candidates/audio-v3/{spec['keepsake_id']}/{spec['variant']}.wav"
        outputs[path] = data
        artifacts.append({"role": "audio_candidate", "candidate_id": f"audio-v3-{spec['keepsake_id']}-{spec['variant']}",
                          "character_id": spec["character_id"], "keepsake_id": spec["keepsake_id"], "variant": spec["variant"],
                          "label": spec["label"], "path": path.relative_to(ROOT).as_posix(), "sha256": sha(data),
                          "license": LICENSE, "source": f"Edited real CC0 friction recording by {SOURCES[spec['source_id']]['author']}; see sources/audio-v3/manifest.json. No synthesized impact or oscillator.",
                          "source_id": spec["source_id"], "source_sha256": SOURCES[spec["source_id"]]["wav_sha256"],
                          "processing": {**spec, "linear_gain": gain, "attack_seconds": .020, "tail_seconds": .050,
                                         "resampling": "none after pinned 48kHz source decode", "compression_or_saturation": False},
                          "approval_status": "pending_user_audio_and_composite_approval", **measured,
                          "crest_factor_db": measured["peak_dbfs"] - measured["rms_dbfs"], "spectrum": spectral,
                          "previous_rejected_candidate_rms_delta_db": measured["rms_dbfs"] - old["rms_dbfs"]})
    assert len({a["sha256"] for a in artifacts}) == 4
    source_manifest = {"schema_version": 1, "sources": SOURCES,
                       "conversion": "FFmpeg 7.1 (imageio-ffmpeg 0.6.0 macOS arm64): -ac 1 -ar 48000 -c:a pcm_s16le",
                       "source_preservation": "Public HQ previews and exact decoded PCM are preserved. Original uploaded masters were not downloaded.",
                       "license_scope": "CC0-1.0 source conditions remain unchanged; no proprietary restriction on the original recordings.",
                       "artifacts": source_artifacts}
    outputs[ROOT / "sources/audio-v3/manifest.json"] = (json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n").encode()
    report = {"schema_version": 1, "candidate_version": "audio-v3", "generator": "build_audio_v3.py",
              "generator_sha256": sha(Path(__file__).read_bytes()), "artifacts": artifacts, "source_artifacts": source_artifacts,
              "status": "pending_user_audio_and_composite_approval",
              "qa": {"method": "exact source hashes, deterministic PCM regeneration, WAV decode/levels, FFT low-band and crest measurements",
                     "human_listening_performed": False,
                     "limitation": "실제 마찰 녹음과 약한 레벨·완만한 시작을 확인했으나 종이/잎의 질감 만족도는 사용자 청취로 선택해야 함"},
              "changes": ["거부된 휴지·잎 합성 타격음을 사용하지 않고 실제 얇은 종이·잎 마찰 녹음으로 교체",
                          "20ms 완만한 시작, 50ms 종료, 저음 제거로 둔탁한 충격 대신 가벼운 마찰 유지",
                          "기존 타격음보다 낮은 RMS와 peak 상한 적용; 음량 경쟁용 과도한 정규화·압축 없음",
                          "테니스공1·어묵1·기존 오리 및 다른 자산·승인 기록은 변경하지 않음"]}
    outputs[ROOT / "audio-v3-review.json"] = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
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
    print(f"{'WROTE' if args.write else 'PASS'}: 4 soft paper/leaf recorded-friction candidates; 4 pinned source media")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
