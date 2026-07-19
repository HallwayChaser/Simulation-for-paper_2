"""Python equivalent and numerical extension of `simulation 8 point Radix.m`.

The original MATLAB file draws an 8-point radix-2 signal-flow graph. This
version preserves that purpose, corrects the left-hand labels to make the
bit-reversed DIT input order explicit, and adds a numerical validation against
NumPy's FFT.

Requirements: numpy, matplotlib
Run from any directory:
    python code/simulation_8_point_radix.py
"""
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
GEN_DIR = ROOT / "generated_figures"
FIG_DIR.mkdir(exist_ok=True)
GEN_DIR.mkdir(exist_ok=True)


def bit_reverse_indices(n: int) -> np.ndarray:
    if n <= 0 or n & (n - 1):
        raise ValueError("n must be a positive power of two")
    bits = int(math.log2(n))
    return np.array([int(f"{i:0{bits}b}"[::-1], 2) for i in range(n)], dtype=int)


def radix2_dit_stages(x: np.ndarray) -> list[np.ndarray]:
    x = np.asarray(x, dtype=np.complex128)
    n = x.size
    order = bit_reverse_indices(n)
    state = x[order].copy()
    stages = [state.copy()]

    group = 2
    while group <= n:
        half = group // 2
        for base in range(0, n, group):
            for local in range(half):
                twiddle = np.exp(-2j * np.pi * local / group)
                a = state[base + local]
                b = state[base + local + half]
                product = twiddle * b
                state[base + local] = a + product
                state[base + local + half] = a - product
        stages.append(state.copy())
        group *= 2
    return stages


def draw_butterfly(ax, x1: float, x2: float, y1: float, y2: float, label: str) -> None:
    ax.plot([x1, x2], [y1, y1], linewidth=0.8, color="black")
    ax.plot([x1, x2], [y2, y2], linewidth=0.8, color="black")
    ax.plot([x1, x2], [y1, y2], linewidth=0.8, color="black")
    ax.plot([x1, x2], [y2, y1], linewidth=0.8, color="black")
    ax.plot(x2, y1, marker=">", markersize=4, color="black")
    ax.plot(x2, y2, marker=">", markersize=4, color="black")
    ax.text((x1 + x2) / 2, min(y1, y2) - 0.18, label, ha="center", va="top", fontsize=8)


def plot_signal_flow_graph() -> Path:
    n = 8
    y = np.linspace(7, 0, n)
    x_positions = [0.0, 1.8, 3.6, 5.4]
    bitrev = bit_reverse_indices(n)

    fig, ax = plt.subplots(figsize=(11.2, 4.8))
    ax.axis("off")

    for row in range(n):
        ax.text(-0.25, y[row], f"x[{bitrev[row]}]", ha="right", va="center", fontsize=9)
        ax.text(5.65, y[row], f"X[{row}]", ha="left", va="center", fontsize=9)
        ax.plot([x_positions[0], x_positions[-1]], [y[row], y[row]], linewidth=0.45, alpha=0.35, color="black")

    stage_pairs = [
        [(0, 1, r"$W_2^0$"), (2, 3, r"$W_2^0$"), (4, 5, r"$W_2^0$"), (6, 7, r"$W_2^0$")],
        [(0, 2, r"$W_4^0$"), (1, 3, r"$W_4^1$"), (4, 6, r"$W_4^0$"), (5, 7, r"$W_4^1$")],
        [(0, 4, r"$W_8^0$"), (1, 5, r"$W_8^1$"), (2, 6, r"$W_8^2$"), (3, 7, r"$W_8^3$")],
    ]

    for stage, pairs in enumerate(stage_pairs):
        for upper, lower, label in pairs:
            draw_butterfly(
                ax,
                x_positions[stage],
                x_positions[stage + 1],
                y[upper],
                y[lower],
                label,
            )
        ax.text(
            (x_positions[stage] + x_positions[stage + 1]) / 2,
            7.65,
            f"Stage {stage + 1}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    ax.text(-0.25, 7.65, "Bit-reversed input", ha="right", va="bottom", fontsize=9)
    ax.text(5.65, 7.65, "Natural-order output", ha="left", va="bottom", fontsize=9)
    ax.set_xlim(-1.05, 6.55)
    ax.set_ylim(-0.55, 8.1)
    ax.set_title("8-Point Radix-2 DIT FFT Signal-Flow Graph", fontweight="bold")
    fig.tight_layout()

    output = FIG_DIR / "fft8_radix2_signal_flow_graph_python.png"
    fig.savefig(output, dpi=300, bbox_inches="tight")
    fig.savefig(GEN_DIR / output.name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_numerical_validation(stages: list[np.ndarray], reference: np.ndarray) -> tuple[Path, float]:
    estimate = stages[-1]
    error = np.abs(estimate - reference)
    max_error = float(np.max(error))
    k = np.arange(reference.size)

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.5))

    axes[0, 0].stem(k, np.abs(reference), linefmt="k-", markerfmt="ko", basefmt=" ", label="NumPy FFT")
    axes[0, 0].plot(k, np.abs(estimate), "ko", fillstyle="none", label="Radix-2 DIT")
    axes[0, 0].set_title("FFT Magnitude")
    axes[0, 0].set_xlabel("Bin k")
    axes[0, 0].set_ylabel("Magnitude")
    axes[0, 0].legend()

    axes[0, 1].stem(k, np.angle(reference), linefmt="k-", markerfmt="ko", basefmt=" ", label="NumPy FFT")
    axes[0, 1].plot(k, np.angle(estimate), "kx", label="Radix-2 DIT")
    axes[0, 1].set_title("FFT Phase")
    axes[0, 1].set_xlabel("Bin k")
    axes[0, 1].set_ylabel("Phase (rad)")
    axes[0, 1].legend()

    axes[1, 0].stem(k, error, linefmt="k-", markerfmt="ko", basefmt=" ")
    axes[1, 0].set_yscale("log")
    axes[1, 0].set_title("Absolute Error")
    axes[1, 0].set_xlabel("Bin k")
    axes[1, 0].set_ylabel("|X_radix2[k]-X_ref[k]|")

    stage_matrix = np.vstack([np.abs(s) for s in stages])
    image = axes[1, 1].imshow(stage_matrix, aspect="auto", interpolation="nearest", cmap="gray_r")
    axes[1, 1].set_title("Magnitude Evolution by Stage")
    axes[1, 1].set_xlabel("RAM/output index")
    axes[1, 1].set_ylabel("State")
    axes[1, 1].set_yticks(range(len(stages)), ["Load", "Stage 1", "Stage 2", "Stage 3"])
    fig.colorbar(image, ax=axes[1, 1], fraction=0.046, pad=0.04, label="Magnitude")

    for ax in axes.flat[:3]:
        ax.grid(True, alpha=0.3)

    fig.suptitle(f"8-Point Radix-2 Validation: maximum error = {max_error:.3e}")
    fig.tight_layout()
    output = FIG_DIR / "fft8_radix2_validation_python.png"
    fig.savefig(output, dpi=300, bbox_inches="tight")
    fig.savefig(GEN_DIR / output.name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output, max_error


def main() -> None:
    x = np.arange(8, dtype=float)
    stages = radix2_dit_stages(x)
    reference = np.fft.fft(x)
    graph_path = plot_signal_flow_graph()
    validation_path, max_error = plot_numerical_validation(stages, reference)

    report_lines = [
        "PYTHON 8-POINT RADIX-2 DIT FFT",
        f"Input: {x.tolist()}",
        f"Bit-reversed order: {bit_reverse_indices(x.size).tolist()}",
        f"Maximum absolute error vs NumPy FFT: {max_error:.16e}",
        f"Figures: {graph_path.name}, {validation_path.name}",
    ]
    for index, state in enumerate(stages):
        report_lines.append(f"State {index}: {np.array2string(state, precision=6)}")
    report = "\n".join(report_lines) + "\n"
    (ROOT / "fft8_python_results.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
