#!/usr/bin/env python3
"""Analyze transistor-level SPICE data and generate paper-ready figures."""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
FIGURES = ROOT / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)


def load_wrdata(path: Path) -> np.ndarray:
    data = np.loadtxt(path, skiprows=1)
    if data.ndim != 2:
        raise ValueError(f"unexpected data shape in {path}")
    return data


def nearest_row(data: np.ndarray, time_seconds: float) -> np.ndarray:
    return data[np.argmin(np.abs(data[:, 0] - time_seconds))]


def parse_measure(log_text: str, name: str) -> float:
    pattern = rf"(?im)^\s*{re.escape(name)}\s*=\s*([+-]?[0-9.]+e[+-][0-9]+)"
    match = re.search(pattern, log_text)
    if not match:
        raise ValueError(f"measure {name} not found")
    return float(match.group(1))


def analyze_full_adder() -> dict[str, object]:
    data = load_wrdata(
        REPORTS / "spice_full_adder" / "full_adder_waveform.dat"
    )
    # time, A, B, CIN, SUM, COUT, I(VDD)
    truth_rows = []
    failures = 0
    for step in range(8):
        sample_time = (0.6 + step) * 1e-9
        row = nearest_row(data, sample_time)
        a, b, cin, sum_v, cout_v = (int(value > 0.9) for value in row[1:6])
        expected_sum = a ^ b ^ cin
        expected_cout = (a & b) | (a & cin) | (b & cin)
        passed = sum_v == expected_sum and cout_v == expected_cout
        failures += int(not passed)
        truth_rows.append(
            {
                "A": a,
                "B": b,
                "Cin": cin,
                "Sum": sum_v,
                "Cout": cout_v,
                "ExpectedSum": expected_sum,
                "ExpectedCout": expected_cout,
                "Pass": passed,
            }
        )
    truth_rows.sort(key=lambda row: (row["A"], row["B"], row["Cin"]))

    log_text = (
        REPORTS / "spice_full_adder" / "simulation.log"
    ).read_text(encoding="utf-8", errors="replace")
    iavg = parse_measure(log_text, "iavg")
    pavg = -1.8 * iavg

    time_ns = data[:, 0] * 1e9
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 4.9), sharex=True)
    input_colors = ("#3c5f8a", "#4f8a65", "#8b5a83")
    for index, (label, color) in enumerate(zip(("A", "B", "Cin"), input_colors), 1):
        axes[0].plot(time_ns, data[:, index] / 1.8 + 1.35 * (3 - index),
                     color=color, linewidth=1.4, label=label)
    axes[0].set_yticks((0.0, 1.35, 2.70))
    axes[0].set_yticklabels(("Cin", "B", "A"))
    axes[0].set_title("36-transistor full-adder exhaustive input sequence")
    axes[0].grid(True, axis="x", alpha=0.25)

    axes[1].plot(time_ns, data[:, 4] / 1.8 + 1.35, color="#b4493f",
                 linewidth=1.5, label="Sum")
    axes[1].plot(time_ns, data[:, 5] / 1.8, color="#6c4c91",
                 linewidth=1.5, label="Cout")
    axes[1].set_yticks((0.0, 1.35))
    axes[1].set_yticklabels(("Cout", "Sum"))
    axes[1].set_xlabel("Time (ns)")
    axes[1].grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "spice_full_adder_waveform.png", dpi=220,
                bbox_inches="tight")
    plt.close(fig)

    return {
        "truth_table": truth_rows,
        "truth_table_failures": failures,
        "average_supply_current_a": iavg,
        "average_dynamic_test_power_w": pavg,
        "transistor_count": 36,
        "model": "generic Level-1 180 nm, 1.8 V, 27 C",
    }


def analyze_ripple() -> dict[str, float]:
    data = load_wrdata(REPORTS / "spice_ripple19" / "ripple19_waveform.dat")
    log_text = (
        REPORTS / "spice_ripple19" / "simulation.log"
    ).read_text(encoding="utf-8", errors="replace")
    rise = parse_measure(log_text, "tpd_rise")
    fall = parse_measure(log_text, "tpd_fall")
    iavg = parse_measure(log_text, "iavg")
    qtrans = parse_measure(log_text, "qtrans")

    time_ns = data[:, 0] * 1e9
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 5.3), sharex=True)
    labels = ("Cin", "C5", "C10", "C15", "Cout")
    colors = ("#222222", "#2c6e9b", "#4d8b62", "#9b7445", "#b0443a")
    for index, (label, color) in enumerate(zip(labels, colors), 1):
        axes[0].plot(time_ns, data[:, index] / 1.8 + 1.2 * (5 - index),
                     linewidth=1.25, color=color, label=label)
    axes[0].set_yticks([1.2 * i for i in range(5)])
    axes[0].set_yticklabels(("Cout", "C15", "C10", "C5", "Cin"))
    axes[0].set_title("Carry propagation through the 19-bit transistor-level adder")
    axes[0].grid(True, axis="x", alpha=0.25)

    supply_current_ua = -data[:, 7] * 1e6
    axes[1].plot(time_ns, supply_current_ua, color="#75518c", linewidth=1.0)
    axes[1].set_ylabel("Supply current (uA)")
    axes[1].set_xlabel("Time (ns)")
    axes[1].grid(True, alpha=0.25)
    axes[1].axvspan(5.0, 7.0, color="#d9896a", alpha=0.12)
    axes[1].axvspan(25.0, 27.0, color="#6b8dc2", alpha=0.12)
    fig.tight_layout()
    fig.savefig(FIGURES / "spice_ripple19_waveform.png", dpi=220,
                bbox_inches="tight")
    plt.close(fig)

    return {
        "carry_rise_delay_s": rise,
        "carry_fall_delay_s": fall,
        "worst_carry_delay_s": max(rise, fall),
        "average_supply_current_a": iavg,
        "average_test_power_w": -1.8 * iavg,
        "transition_window_charge_c": qtrans,
        "transition_window_energy_j": -1.8 * qtrans,
        "full_adders": 19,
        "transistor_count": 19 * 36,
    }


def draw_full_adder_topology() -> None:
    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    def nand(x: float, y: float, name: str) -> None:
        patch = plt.Rectangle((x, y), 1.25, 0.68, facecolor="#eaf1f7",
                              edgecolor="#244f73", linewidth=1.2)
        ax.add_patch(patch)
        ax.text(x + 0.625, y + 0.34, name, ha="center", va="center",
                fontsize=8)

    # Gate placement follows the exact FA36 netlist.
    positions = {
        "NAB": (1.5, 5.3), "NA": (3.3, 6.0), "NB": (3.3, 4.7),
        "X1": (5.1, 5.35), "NCX": (6.8, 3.9), "NX": (8.4, 5.15),
        "NC": (8.4, 3.45), "SUM": (10.2, 4.3), "COUT": (8.4, 1.5),
    }
    for name, (x, y) in positions.items():
        nand(x, y, f"NAND\n{name}")

    ax.text(0.3, 6.1, "A", fontsize=10, weight="bold")
    ax.text(0.3, 5.35, "B", fontsize=10, weight="bold")
    ax.text(5.25, 3.0, "Cin", fontsize=10, weight="bold")
    ax.text(11.55, 4.64, "Sum", fontsize=10, weight="bold", ha="right")
    ax.text(10.0, 1.84, "Cout", fontsize=10, weight="bold")

    def arrow(x1: float, y1: float, x2: float, y2: float) -> None:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#4b5560",
                                    linewidth=1.0))

    arrow(0.55, 6.0, 1.5, 5.78)
    arrow(0.55, 5.3, 1.5, 5.52)
    arrow(2.75, 5.64, 3.3, 6.20)
    arrow(2.75, 5.64, 3.3, 4.90)
    arrow(0.55, 6.0, 3.3, 6.40)
    arrow(0.55, 5.3, 3.3, 4.75)
    arrow(4.55, 6.2, 5.1, 5.78)
    arrow(4.55, 5.0, 5.1, 5.52)
    arrow(6.35, 5.69, 6.8, 4.24)
    arrow(5.65, 3.12, 6.8, 4.00)
    arrow(8.05, 4.24, 8.4, 5.42)
    arrow(6.35, 5.55, 8.4, 5.30)
    arrow(8.05, 4.06, 8.4, 3.77)
    arrow(5.65, 3.12, 8.4, 3.56)
    arrow(9.65, 5.40, 10.2, 4.74)
    arrow(9.65, 3.78, 10.2, 4.48)
    arrow(11.45, 4.64, 11.7, 4.64)
    arrow(2.75, 5.50, 8.4, 1.75)
    arrow(8.05, 4.00, 8.4, 1.95)
    arrow(9.65, 1.84, 10.05, 1.84)

    ax.text(0.4, 0.45,
            "Each NAND2 is a 4-transistor static-CMOS gate; "
            "9 NAND2 instances yield a 36-transistor full adder.",
            fontsize=9, color="#343a40")
    fig.tight_layout()
    fig.savefig(FIGURES / "full_adder_36t_topology.png", dpi=220,
                bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    full_adder = analyze_full_adder()
    ripple = analyze_ripple()
    draw_full_adder_topology()
    summary = {"full_adder": full_adder, "ripple19": ripple}
    (REPORTS / "spice_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    with (REPORTS / "spice_truth_table.csv").open(
        "w", encoding="utf-8"
    ) as stream:
        stream.write("A,B,Cin,Sum,Cout,ExpectedSum,ExpectedCout,Pass\n")
        for row in full_adder["truth_table"]:
            stream.write(
                f"{row['A']},{row['B']},{row['Cin']},{row['Sum']},"
                f"{row['Cout']},{row['ExpectedSum']},{row['ExpectedCout']},"
                f"{int(row['Pass'])}\n"
            )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
