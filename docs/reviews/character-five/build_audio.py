#!/usr/bin/env python3
"""Deterministic, original collision-only sound candidates for local review.

Default is read-only verification. --write rebuilds ten synthesized WAV files,
one unchanged reference copy, and measured metadata. No recordings are sampled
into the new sounds; no launch, flight, music, voice, or reverb layer is added.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import wave

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[2]
RATE = 48000
TAU = 2 * math.pi
PEAK_LIMIT = .27
LICENSE = "SIDEY Paid Asset License 1.0 (package scope: LICENSE.md)"
REFERENCE = "assets/v1/audio/impact-throwable_baseball.wav"
REFERENCE_SHA256 = "f1d696062f945f5bd47e5c7d94f65ff7c46c26e69a2d14a6d76f7532b989f35c"
SPECS = {
    "tennis_ball": {"character_id": "pixel_shiba", "variants": {
        "A": {"duration": .17, "label": "톡 · 가볍고 단단한 고무 접촉", "frequency": 330, "decay": 31, "noise": .18},
        "B": {"duration": .23, "label": "통 · 낮고 탄성 있는 공 울림", "frequency": 210, "decay": 21, "noise": .10}}},
    "rubber_duck": {"character_id": "pixel_duck", "variants": {
        "A": {"duration": .16, "label": "삑 · 짧고 또렷한 고무 오리", "frequency": 770, "sweep": -140, "harmonic": .24},
        "B": {"duration": .23, "label": "뀩 · 낮게 눌렸다 풀리는 오리", "frequency": 480, "sweep": 240, "harmonic": .30}}},
    "tissue_ball": {"character_id": "pixel_poop", "variants": {
        "A": {"duration": .15, "label": "퍽 · 보송하고 낮은 종이 접촉", "texture_rate": 34, "decay": 25, "low_mix": .90},
        "B": {"duration": .21, "label": "푸슥 · 접힌 종이가 짧게 구겨지는 질감", "texture_rate": 61, "decay": 18, "low_mix": .35}}},
    "fish_cake_skewer": {"character_id": "pixel_tteokbokki", "variants": {
        "A": {"duration": .16, "label": "찹 · 촉촉하고 짧은 어묵 접촉", "frequency": 260, "sweep": -100, "wet_mix": .90},
        "B": {"duration": .22, "label": "촵 · 말랑하게 눌리는 어묵", "frequency": 180, "sweep": 120, "wet_mix": .55}}},
    "leaf": {"character_id": "pixel_quokka", "variants": {
        "A": {"duration": .13, "label": "파삭 · 얇고 마른 잎의 짧은 접촉", "texture_rate": 91, "decay": 31, "low_mix": .10},
        "B": {"duration": .20, "label": "바스락 · 부드럽게 접히는 잎", "texture_rate": 47, "decay": 20, "low_mix": .48}}},
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode(data: bytes) -> tuple[list[int], int]:
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels(), wav.getcomptype()) == (RATE, 2, 1, "NONE")
        count = wav.getnframes()
        pcm = wav.readframes(count)
    assert count and len(pcm) == count * 2
    return list(struct.unpack(f"<{count}h", pcm)), count


def metrics(data: bytes) -> dict:
    samples, count = decode(data)
    peak = max(abs(value) for value in samples) / 32768
    rms = math.sqrt(sum(value * value for value in samples) / count) / 32768
    return {"duration_seconds": count / RATE, "sample_rate": RATE, "channels": 1,
            "bit_depth": 16, "encoding": "PCM signed little-endian",
            "sample_count": count, "peak": peak, "rms": rms,
            "peak_dbfs": 20 * math.log10(peak), "rms_dbfs": 20 * math.log10(rms),
            "clipped_samples": sum(value <= -32768 or value >= 32767 for value in samples),
            "first_sample": samples[0], "last_sample": samples[-1],
            "dc_offset": sum(samples) / count / 32768}


def synthesize(key: str, variant: str, spec: dict, target_rms: float) -> bytes:
    seed = int.from_bytes(hashlib.sha256(f"SIDEY:{key}:{variant}:audio-v1".encode()).digest()[:4], "little")
    phase = low = slow = output_low = output_smooth = 0.0
    values = []
    duration = spec["duration"]
    count = round(duration * RATE)
    for i in range(count):
        t = i / RATE
        u = t / duration
        # Fully specified LCG: cross-process stable texture without recordings.
        seed = (1664525 * seed + 1013904223) & 0xffffffff
        white = seed / 2147483648 - 1
        low += .22 * (white - low)
        slow += .045 * (low - slow)
        grain = low - slow
        if key == "tennis_ball":
            # Damped rubber body modes with a very short felt contact texture.
            frequency = spec["frequency"] * (1 + .23 * math.exp(-30 * t))
            phase += TAU * frequency / RATE
            body = (math.sin(phase) + .18 * math.sin(phase * 1.73)) * math.exp(-spec["decay"] * t)
            value = body + spec["noise"] * low * math.exp(-70 * t)
        elif key == "rubber_duck":
            # One squeeze only; harmonics remain below 4kHz and no square wave.
            frequency = spec["frequency"] + spec["sweep"] * u + 11 * math.sin(TAU * 17 * t)
            phase += TAU * frequency / RATE
            body = math.sin(phase) + spec["harmonic"] * math.sin(3 * phase) + .065 * math.sin(5 * phase)
            envelope = math.sin(math.pi * u) ** .8 * math.exp(-1.4 * u)
            value = body * envelope + .055 * low * math.exp(-45 * t)
        elif key == "tissue_ball":
            # Noise microstructure belongs to one continuous crumple envelope.
            texture = spec["low_mix"] * slow * 4 + (1 - spec["low_mix"]) * grain * 2
            texture *= .68 + .32 * math.sin(TAU * spec["texture_rate"] * t) ** 2
            envelope = (1 - math.exp(-400 * t)) * math.exp(-spec["decay"] * t)
            value = texture * envelope + .055 * math.sin(TAU * 145 * t) * math.exp(-48 * t)
        elif key == "fish_cake_skewer":
            frequency = spec["frequency"] + spec["sweep"] * u
            phase += TAU * frequency / RATE
            body = math.sin(phase + .22 * math.sin(phase)) * math.exp(-22 * t)
            wet = (low * .8 + slow * 3) * math.exp(-32 * t)
            # Small wooden contact accompanies the same impact onset.
            stick = .035 * math.sin(TAU * 890 * t) * math.exp(-75 * t)
            value = .34 * body + spec["wet_mix"] * wet + stick
        elif key == "leaf":
            texture = (1 - spec["low_mix"]) * grain + spec["low_mix"] * slow * 3
            texture *= .40 + .60 * math.sin(TAU * spec["texture_rate"] * t) ** 2
            value = texture * (1 - math.exp(-650 * t)) * math.exp(-spec["decay"] * t)
        else:
            raise ValueError(key)
        # Two low-pass stages tame high-frequency transients across candidates.
        output_low += .36 * (value - output_low)
        output_smooth += .36 * (output_low - output_smooth)
        values.append(output_smooth)

    if key in ("tissue_ball", "fish_cake_skewer", "leaf"):
        # Gentle continuous saturation lowers noise crest factor without sample
        # truncation; another low-pass stage tames the added harmonics.
        peak = max(abs(value) for value in values)
        previous = 0.0
        for i, value in enumerate(values):
            previous += .30 * (math.tanh(3 * value / peak) - previous)
            values[i] = previous
    # Remove DC before edge ramps; no digital clipping or trailing hard cut.
    mean = sum(values) / count
    values = [(value - mean) * min(1, i / (RATE * .002))
              * min(1, (count - 1 - i) / (RATE * .015)) for i, value in enumerate(values)]
    rms = math.sqrt(sum(value * value for value in values) / count)
    peak = max(abs(value) for value in values)
    gain = min(target_rms / rms, PEAK_LIMIT / peak)
    pcm = [round(value * gain * 32768) for value in values]
    assert all(-32768 < value < 32767 for value in pcm), "clipping must never be fixed by truncation"
    assert pcm[0] == pcm[-1] == 0
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(struct.pack(f"<{count}h", *pcm))
    return stream.getvalue()


def build() -> dict[Path, bytes]:
    reference_data = (REPOSITORY / REFERENCE).read_bytes()
    assert digest(reference_data) == REFERENCE_SHA256, "review changed reference audio before regenerating"
    reference_metrics = metrics(reference_data)
    assert not reference_metrics["clipped_samples"]
    reference_path = ROOT / "references/impact-baseball.wav"
    outputs = {reference_path: reference_data}
    artifacts = [{"role": "audio_reference", "variant": "reference",
                  "candidate_id": "audio-reference-impact-baseball",
                  "path": str(reference_path.relative_to(ROOT)), "sha256": digest(reference_data),
                  "source": f"기존 SIDEY {REFERENCE}의 변경 없는 복사; 합성 입력으로 사용하지 않음",
                  "source_path": REFERENCE, "source_sha256": digest(reference_data),
                  "license": LICENSE, **reference_metrics}]
    for key, definition in SPECS.items():
        for variant, spec in definition["variants"].items():
            data = synthesize(key, variant, spec, reference_metrics["rms"])
            measured = metrics(data)
            assert measured["clipped_samples"] == 0
            assert measured["peak"] <= PEAK_LIMIT + 1 / 32768
            assert abs(measured["rms_dbfs"] - reference_metrics["rms_dbfs"]) < 3, "comparison RMS differs by 3dB or more"
            path = ROOT / "candidates/audio-v1" / key / f"{variant}.wav"
            outputs[path] = data
            artifacts.append({"role": "audio_candidate", "character_id": definition["character_id"],
                              "keepsake_id": key, "variant": variant,
                              "candidate_id": f"audio-v1-{key}-{variant}",
                              "path": str(path.relative_to(ROOT)), "sha256": digest(data),
                              "label": spec["label"], "source": "Codex original deterministic stdlib synthesis in build_audio.py; no external recordings or commercial samples",
                              "license": LICENSE, "synthesis_parameters": spec,
                              "approval_status": "pending_user_audio_and_composite_approval", **measured,
                              "reference_peak_delta_db": measured["peak_dbfs"] - reference_metrics["peak_dbfs"],
                              "reference_rms_delta_db": measured["rms_dbfs"] - reference_metrics["rms_dbfs"]})
    assert len({entry["sha256"] for entry in artifacts}) == 11, "A/B candidates must differ"
    report = {"schema_version": 1, "candidate_version": "audio-v1",
              "status": "pending_user_audio_and_composite_approval",
              "generator": "build_audio.py", "generator_sha256": digest(Path(__file__).read_bytes()),
              "source_policy": "신규 10개는 코드 원합성. 기존 야구공 WAV는 변경 없는 비교용 복사이며 신규 합성에 샘플링하지 않음",
              "synthesis_rules": ["충돌 한 번당 음원 한 번; 비행·발사음·음성·음악·잔향 없음",
                                  "고정 SHA-256 seed 및 명시된 LCG를 사용한 잡음과 감쇠 사인파 합성",
                                  "2단 저역 통과 필터, 2ms 시작·15ms 종료 램프로 고주파와 끝 클릭 억제",
                                  "휴지·어묵·잎의 잡음 peak는 연속 tanh 압축 후 추가 저역 통과로 완화; 샘플 잘라내기 없음",
                                  "기존 야구공 full-file RMS를 목표로 정규화, peak 0.27 이하; 하드클리핑 없음",
                                  "A/B는 지속시간·공명 주파수·질감으로 구분; 어느 것도 최종 선택으로 표시하지 않음"],
              "qa": {"method": "stdlib WAV decode, measured PCM levels, deterministic byte regeneration, start/end zero samples",
                     "human_listening_performed": False,
                     "limitation": "음색의 자연스러움·인지 음량은 수치 검사로 승인할 수 없음. 사용자가 예시 페이지에서 A/B·기준음·합성을 직접 청취해야 함",
                     "reference_rms_dbfs": reference_metrics["rms_dbfs"], "peak_limit": PEAK_LIMIT},
              "artifacts": artifacts}
    outputs[ROOT / "audio-review.json"] = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="explicitly regenerate WAV candidates and measured metadata")
    args = parser.parse_args()
    for path, data in build().items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        elif not path.exists() or path.read_bytes() != data:
            print(f"FAIL: stale/missing {path.relative_to(ROOT)}")
            return 1
    print(f"{'WROTE' if args.write else 'PASS'}: 10 deterministic collision candidates + unchanged baseball reference; listening approval pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
