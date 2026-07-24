#!/usr/bin/env python3
"""Independent consistency tests for the FFT8 fixed-point data contract."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model"))

from fft8_fixed_model import (  # noqa: E402
    BIT_REVERSE_3,
    SCHEDULE,
    FixedFormat,
    fft8_fixed,
    round_shift_away,
    twiddle_multiply,
)


def independent_round(value: int, shift: int) -> int:
    if shift <= 0:
        return value << (-shift)
    denominator = 1 << shift
    magnitude = abs(value)
    quotient, remainder = divmod(magnitude, denominator)
    if 2 * remainder >= denominator:
        quotient += 1
    return quotient if value >= 0 else -quotient


def float_schedule(samples: np.ndarray) -> np.ndarray:
    memory = np.zeros(8, dtype=np.complex128)
    for natural_index, value in enumerate(samples):
        memory[BIT_REVERSE_3[natural_index]] = value
    for stage in SCHEDULE:
        for address_a, address_b, selector in stage:
            twiddle = np.exp(-2j * math.pi * selector / 8.0)
            a = memory[address_a]
            t = memory[address_b] * twiddle
            memory[address_a] = a + t
            memory[address_b] = a - t
    return memory


def baseline_twiddle(
    b_re: int, b_im: int, selector: int, fmt: FixedFormat
) -> tuple[int, int]:
    c = fmt.coefficient
    if selector == 0:
        return b_re, b_im
    if selector == 2:
        return b_im, -b_re
    if selector == 1:
        wr, wi = c, -c
    elif selector == 3:
        wr, wi = -c, -c
    else:
        raise ValueError(selector)
    real_product = b_re * wr - b_im * wi
    imag_product = b_re * wi + b_im * wr
    return (
        independent_round(real_product, fmt.frac),
        independent_round(imag_product, fmt.frac),
    )


def parse_hex16(text: str) -> int:
    raw = int(text, 16)
    return raw - 65536 if raw & 0x8000 else raw


def check_rounding() -> int:
    cases = 0
    for value in range(-300_000, 300_001):
        if round_shift_away(value, 1) != independent_round(value, 1):
            raise AssertionError(f"stage rounding mismatch at {value}")
        cases += 1
    rng = np.random.default_rng(0x51A7)
    for value in rng.integers(-(1 << 33), 1 << 33, size=250_000, dtype=np.int64):
        integer = int(value)
        if round_shift_away(integer, 15) != independent_round(integer, 15):
            raise AssertionError(f"coefficient rounding mismatch at {integer}")
        cases += 1
    return cases


def check_twiddles() -> int:
    fmt = FixedFormat(16)
    edge_values = (
        fmt.minimum,
        fmt.minimum + 1,
        -23170,
        -16384,
        -3,
        -2,
        -1,
        0,
        1,
        2,
        3,
        16384,
        23170,
        fmt.maximum - 1,
        fmt.maximum,
    )
    cases = 0
    for b_re in edge_values:
        for b_im in edge_values:
            for selector in range(4):
                actual = twiddle_multiply(b_re, b_im, selector, fmt)
                expected = baseline_twiddle(b_re, b_im, selector, fmt)
                if actual != expected:
                    raise AssertionError(
                        f"twiddle mismatch ({b_re},{b_im}) W{selector}: "
                        f"{actual} != {expected}"
                    )
                cases += 1

    rng = np.random.default_rng(0x7A31)
    values = rng.integers(
        fmt.minimum, fmt.maximum + 1, size=(250_000, 2), dtype=np.int64
    )
    for index, pair in enumerate(values):
        selector = index & 3
        b_re, b_im = int(pair[0]), int(pair[1])
        if twiddle_multiply(b_re, b_im, selector, fmt) != baseline_twiddle(
            b_re, b_im, selector, fmt
        ):
            raise AssertionError("random twiddle baseline mismatch")
        cases += 1
    return cases


def check_float_schedule() -> tuple[int, float]:
    rng = np.random.default_rng(0x8F17)
    maximum_error = 0.0
    frame_count = 20_000
    for _ in range(frame_count):
        frame = rng.normal(size=8) + 1j * rng.normal(size=8)
        error = np.max(np.abs(float_schedule(frame) - np.fft.fft(frame)))
        maximum_error = max(maximum_error, float(error))
    if maximum_error > 1e-11:
        raise AssertionError(f"radix-2 schedule error {maximum_error}")
    return frame_count, maximum_error


def check_vectors() -> dict[str, int | str]:
    csv_path = ROOT / "testvectors" / "fft8_vectors.csv"
    mem_path = ROOT / "testvectors" / "fft8_vectors.mem"
    if not csv_path.exists() or not mem_path.exists():
        raise FileNotFoundError("run model/fft8_fixed_model.py first")

    memory_words = mem_path.read_text(encoding="ascii").split()
    rows = list(csv.reader(csv_path.open(encoding="utf-8")))
    header, data_rows = rows[0], rows[1:]
    if len(header) != 34:
        raise AssertionError(f"vector CSV header has {len(header)} fields")
    if len(data_rows) != 2009:
        raise AssertionError(f"expected 2009 frames, got {len(data_rows)}")
    if len(memory_words) != len(data_rows) * 32:
        raise AssertionError("flat XSim memory word count does not match CSV")

    saturation_frames = 0
    cursor = 0
    for frame_index, row in enumerate(data_rows):
        if len(row) != 34:
            raise AssertionError(f"frame {frame_index} has {len(row)} fields")
        if int(row[0]) != frame_index:
            raise AssertionError("frame index sequence is not contiguous")
        csv_words = [word.upper() for word in row[2:]]
        if memory_words[cursor : cursor + 32] != csv_words:
            raise AssertionError(f"CSV/MEM serialization mismatch at frame {frame_index}")
        cursor += 32

        inputs = [
            (parse_hex16(row[2 + 2 * i]), parse_hex16(row[3 + 2 * i]))
            for i in range(8)
        ]
        expected = [
            (parse_hex16(row[18 + 2 * i]), parse_hex16(row[19 + 2 * i]))
            for i in range(8)
        ]
        actual, saturations, _ = fft8_fixed(inputs, 16)
        if actual != expected:
            raise AssertionError(f"golden vector drift at frame {frame_index}")
        saturation_frames += int(saturations > 0)

    if saturation_frames != 1:
        raise AssertionError(
            f"expected exactly one saturation frame, got {saturation_frames}"
        )
    return {
        "frames": len(data_rows),
        "words": len(memory_words),
        "outputs": len(data_rows) * 8,
        "saturation_frames": saturation_frames,
        "memory_sha256": hashlib.sha256(mem_path.read_bytes()).hexdigest(),
    }


def main() -> None:
    fmt = FixedFormat(16)
    if fmt.coefficient != 23170:
        raise AssertionError(f"Q1.15 coefficient is {fmt.coefficient}, not 23170")
    if sum(len(stage) for stage in SCHEDULE) != 12:
        raise AssertionError("radix-2 schedule must contain 12 butterflies")

    rounding_cases = check_rounding()
    twiddle_cases = check_twiddles()
    floating_frames, floating_error = check_float_schedule()
    vectors = check_vectors()

    schedule_twiddles = [entry[2] for stage in SCHEDULE for entry in stage]
    per_frame_coverage = {
        f"W8^{selector}": schedule_twiddles.count(selector) for selector in range(4)
    }
    if per_frame_coverage != {"W8^0": 7, "W8^1": 1, "W8^2": 3, "W8^3": 1}:
        raise AssertionError(f"unexpected twiddle schedule {per_frame_coverage}")

    result = {
        "result": "PASS",
        "coefficient_q15": fmt.coefficient,
        "rounding_cases_checked": rounding_cases,
        "twiddle_cases_checked": twiddle_cases,
        "floating_schedule_frames": floating_frames,
        "floating_schedule_max_error": floating_error,
        "vectors": vectors,
        "per_frame_twiddle_coverage": per_frame_coverage,
    }
    output = ROOT / "reports" / "reference" / "model_consistency.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        "PASS: "
        f"rounding={rounding_cases} twiddle={twiddle_cases} "
        f"float_frames={floating_frames} vectors={vectors['frames']}"
    )


if __name__ == "__main__":
    main()

