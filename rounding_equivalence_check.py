#!/usr/bin/env python3
"""Render selected RTL VCD signals as a compact paper-ready waveform."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIVADO_VCD = ROOT / "reports" / "vivado" / "xsim_tone_bin1.vcd"
DEFAULT_REFERENCE_VCD = ROOT / "reports" / "reference" / "rtl_tone_bin1.vcd"
OUTPUT_PATH = ROOT / "figures" / "rtl_waveform.png"


def parse_vcd(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, int]]:
    identifiers: dict[str, tuple[str, int]] = {}
    values: dict[str, int] = {}
    widths: dict[str, int] = {}
    samples: list[tuple[int, dict[str, int]]] = []
    current_time: int | None = None
    in_header = True

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if in_header:
            if line.startswith("$var"):
                fields = line.split()
                width = int(fields[2])
                identifier = fields[3]
                name = fields[4]
                identifiers[identifier] = (name, width)
                widths[name] = width
                values[name] = 0
            elif line.startswith("$enddefinitions"):
                in_header = False
            continue

        if line.startswith("#"):
            new_time = int(line[1:])
            if current_time is not None and new_time != current_time:
                samples.append((current_time, values.copy()))
            current_time = new_time
        elif line.startswith("b"):
            binary, identifier = line[1:].split()
            name, _ = identifiers[identifier]
            values[name] = int(binary.replace("x", "0").replace("z", "0"), 2)
        elif line[0] in "01xz":
            identifier = line[1:]
            name, _ = identifiers[identifier]
            values[name] = 1 if line[0] == "1" else 0
    if current_time is not None:
        samples.append((current_time, values.copy()))

    time = np.asarray([sample[0] for sample in samples], dtype=float)
    signals = {
        name: np.asarray([sample[1][name] for sample in samples], dtype=float)
        for name in widths
    }
    return time, signals, widths


def signed(signal: np.ndarray, width: int) -> np.ndarray:
    raw = signal.astype(np.int64)
    sign = 1 << (width - 1)
    return np.where(raw & sign, raw - (1 << width), raw)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vcd", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    vcd_path = args.vcd
    if vcd_path is None:
        vcd_path = (
            DEFAULT_VIVADO_VCD
            if DEFAULT_VIVADO_VCD.exists()
            else DEFAULT_REFERENCE_VCD
        )
    time, sig, widths = parse_vcd(vcd_path)
    fig, axes = plt.subplots(
        4, 1, figsize=(10.5, 7.6), sharex=True,
        gridspec_kw={"height_ratios": [1.25, 1.25, 1.6, 1.4]},
    )

    control = ("start", "in_valid", "out_valid", "done")
    colors = ("#365f91", "#4d8663", "#b45a43", "#73508e")
    for offset, (name, color) in enumerate(zip(control, colors)):
        axes[0].step(time, sig[name] + 1.35 * (len(control) - 1 - offset),
                     where="post", color=color, linewidth=1.45)
    axes[0].set_yticks([1.35 * i for i in range(4)])
    axes[0].set_yticklabels(("done", "out_valid", "in_valid", "start"))
    axes[0].set_title("RTL transaction: LOAD, 12 butterfly cycles, and natural-order OUTPUT")
    axes[0].grid(True, axis="x", alpha=0.25)

    state = sig["debug_state"]
    compute_mask = state == 2
    stage = np.where(compute_mask, sig["debug_stage"], np.nan)
    butterfly = np.where(compute_mask, sig["debug_butterfly"], np.nan)
    twiddle = np.where(compute_mask, sig["debug_twiddle"], np.nan)
    axes[1].step(time, state, where="post", color="#252525", linewidth=1.4,
                 label="FSM state")
    axes[1].step(time, stage + 4.2, where="post", color="#2d6f95",
                 linewidth=1.2, label="stage")
    axes[1].step(time, butterfly + 7.6, where="post", color="#588b57",
                 linewidth=1.2, label="butterfly")
    axes[1].step(time, twiddle + 12.0, where="post", color="#a76545",
                 linewidth=1.2, label="twiddle")
    axes[1].set_yticks((1.5, 5.2, 9.1, 13.5))
    axes[1].set_yticklabels(("state", "stage", "butterfly", r"$W_8^k$"))
    axes[1].grid(True, axis="x", alpha=0.25)

    compute_time = np.where(compute_mask, time, np.nan)
    for name, label, color in (
        ("debug_a_re", "A.real", "#345e88"),
        ("debug_b_re", "B.real", "#4e865e"),
        ("debug_t_re", "T.real", "#a2613e"),
        ("debug_y0_re", "Y0.real", "#7d4f8c"),
        ("debug_y1_re", "Y1.real", "#b34444"),
    ):
        values = signed(sig[name], widths[name]) / 32768.0
        axes[2].plot(compute_time, np.where(compute_mask, values, np.nan),
                     drawstyle="steps-post", linewidth=1.15, label=label,
                     color=color)
    axes[2].set_ylabel("Q1.15 value")
    axes[2].legend(ncol=5, fontsize=7.5, loc="upper center")
    axes[2].grid(True, alpha=0.25)

    output_mask = sig["out_valid"] == 1
    out_re = signed(sig["out_re"], widths["out_re"]) / 32768.0
    out_im = signed(sig["out_im"], widths["out_im"]) / 32768.0
    axes[3].step(time, np.where(output_mask, out_re, np.nan), where="post",
                 color="#2f6290", linewidth=1.45, label="out.real")
    axes[3].step(time, np.where(output_mask, out_im, np.nan), where="post",
                 color="#b04b3f", linewidth=1.45, label="out.imag")
    axes[3].step(time, np.where(output_mask, sig["out_index"] / 7.0, np.nan),
                 where="post", color="#555555", linewidth=1.0,
                 linestyle="--", label="index/7")
    axes[3].set_ylabel("Output")
    axes[3].set_xlabel("Simulation time (ns)")
    axes[3].legend(ncol=3, fontsize=8, loc="upper right")
    axes[3].grid(True, alpha=0.25)

    for axis in axes:
        axis.set_xlim(0, max(time))
    fig.tight_layout()
    fig.savefig(args.output, dpi=230, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
