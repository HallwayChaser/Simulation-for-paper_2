"""Reproducible FFT experiments used in the IEEE paper.

Requirements: numpy, matplotlib
Run from the project root:
    python code/consolidated_fft_simulation.py

The script prints validation metrics and writes regenerated figures to
`generated_figures/`. The paper uses the supplied project figures by default.
"""
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated_figures"
OUT.mkdir(exist_ok=True)


def direct_dft(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.complex128)
    n = np.arange(x.size)
    kernel = np.exp(-2j * np.pi * np.outer(n, n) / x.size)
    return kernel @ x


def bit_reverse_indices(n: int) -> np.ndarray:
    if n <= 0 or n & (n - 1):
        raise ValueError("n must be a positive power of two")
    bits = int(math.log2(n))
    result = []
    for i in range(n):
        b = f"{i:0{bits}b}"
        result.append(int(b[::-1], 2))
    return np.asarray(result, dtype=int)


def radix2_inplace_trace(x: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    x = np.asarray(x, dtype=np.complex128)
    n = x.size
    ram = np.empty(n, dtype=np.complex128)
    ram[bit_reverse_indices(n)] = x
    trace = [ram.copy()]
    group = 2
    while group <= n:
        half = group // 2
        for base in range(0, n, group):
            for local in range(half):
                w = np.exp(-2j * np.pi * local / group)
                a = ram[base + local]
                b = ram[base + local + half]
                t = b * w
                ram[base + local] = a + t
                ram[base + local + half] = a - t
        trace.append(ram.copy())
        group *= 2
    return ram, trace


def q1_saturate(z: np.ndarray | complex, bits: int) -> tuple[np.ndarray, int]:
    if bits < 2:
        raise ValueError("bits must be at least 2")
    step = 2.0 ** (-(bits - 1))
    upper = 1.0 - step
    arr = np.asarray(z, dtype=np.complex128)
    re_unclipped = np.round(arr.real / step) * step
    im_unclipped = np.round(arr.imag / step) * step
    sat = int(np.count_nonzero((re_unclipped < -1.0) | (re_unclipped > upper)))
    sat += int(np.count_nonzero((im_unclipped < -1.0) | (im_unclipped > upper)))
    re = np.clip(re_unclipped, -1.0, upper)
    im = np.clip(im_unclipped, -1.0, upper)
    return re + 1j * im, sat


def fixed_fft_stage_quantized(
    x: np.ndarray, bits: int, scale_each_stage: bool
) -> tuple[np.ndarray, int]:
    xq, sat_total = q1_saturate(np.asarray(x, dtype=np.complex128), bits)
    n = xq.size
    ram = np.empty(n, dtype=np.complex128)
    ram[bit_reverse_indices(n)] = xq

    group = 2
    while group <= n:
        half = group // 2
        for base in range(0, n, group):
            for local in range(half):
                # Coefficients are quantized, but coefficient clipping is not
                # counted as a data-path saturation event in the reported table.
                w, _ = q1_saturate(np.exp(-2j * np.pi * local / group), bits)
                a = ram[base + local]
                b = ram[base + local + half]
                y0 = a + b * w
                y1 = a - b * w
                if scale_each_stage:
                    y0 /= 2.0
                    y1 /= 2.0
                y0q, sat0 = q1_saturate(y0, bits)
                y1q, sat1 = q1_saturate(y1, bits)
                sat_total += sat0 + sat1
                ram[base + local] = y0q
                ram[base + local + half] = y1q
        group *= 2
    return ram, sat_total


def error_metrics(reference: np.ndarray, estimate: np.ndarray) -> tuple[float, float, float]:
    error = estimate - reference
    ref_energy = float(np.sum(np.abs(reference) ** 2))
    err_energy = float(np.sum(np.abs(error) ** 2))
    snr_db = 10.0 * math.log10(ref_energy / err_energy)
    evm_percent = 100.0 * math.sqrt(err_energy / ref_energy)
    max_error = float(np.max(np.abs(error)))
    return snr_db, evm_percent, max_error


def experiment_dft_fft() -> None:
    x = np.array([1, 2, 3, 4], dtype=np.complex128)
    xd = direct_dft(x)
    xf = np.fft.fft(x)
    err = np.abs(xd - xf)
    print(f"DFT/FFT max error: {err.max():.16e}")

    k = np.arange(x.size)
    fig, axes = plt.subplots(2, 2, figsize=(9, 6))
    axes[0, 0].stem(k, np.abs(xd), basefmt=" ", label="Direct DFT")
    axes[0, 0].plot(k, np.abs(xf), "o", label="NumPy FFT")
    axes[0, 0].set_title("Magnitude")
    axes[0, 0].legend()
    axes[0, 1].stem(k, np.angle(xd), basefmt=" ", label="Direct DFT")
    axes[0, 1].plot(k, np.angle(xf), "o", label="NumPy FFT")
    axes[0, 1].set_title("Phase")
    axes[0, 1].legend()
    axes[1, 0].stem(k, err, basefmt=" ")
    axes[1, 0].set_title("Absolute Error")
    axes[1, 1].axis("off")
    axes[1, 1].text(0.05, 0.65, f"x = [1, 2, 3, 4]\nmax error = {err.max():.3e}")
    for ax in axes.flat:
        if ax.axison:
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Bin k")
    fig.tight_layout()
    fig.savefig(OUT / "dft_fft_validation_regenerated.png", dpi=180)
    plt.close(fig)


def experiment_growth() -> None:
    n = np.array([64, 256, 1024], dtype=float)
    dft = n**2
    fft = n * np.log2(n)
    print("Growth proxy:")
    for ni, di, fi in zip(n.astype(int), dft.astype(int), fft.astype(int)):
        print(f"  N={ni:4d}: N^2={di:8d}, Nlog2N={fi:6d}, ratio={di/fi:.4f}")

    dense = 2 ** np.arange(2, 13)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.loglog(dense, dense**2, marker="o", label=r"$N^2$")
    ax.loglog(dense, dense * np.log2(dense), marker="s", label=r"$N\log_2N$")
    ax.set_xlabel("Transform length N")
    ax.set_ylabel("Growth proxy")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "complexity_growth_regenerated.png", dpi=180)
    plt.close(fig)


def experiment_ram_trace() -> None:
    x = np.arange(8, dtype=float)
    out, trace = radix2_inplace_trace(x)
    err = np.max(np.abs(out - np.fft.fft(x)))
    print(f"In-place FFT max error: {err:.16e}")
    for stage, state in enumerate(trace):
        print(f"  state {stage}: {np.array2string(state, precision=4)}")


def experiment_fixed_point() -> None:
    nfft = 256
    fs = 1024.0
    n = np.arange(nfft)
    x = 0.55 * np.sin(2 * np.pi * 48 * n / fs) + 0.30 * np.sin(2 * np.pi * 120 * n / fs)
    x_ref = np.fft.fft(x)
    rows = []
    for bits in (8, 12, 16):
        for scaled in (True, False):
            estimate, sat = fixed_fft_stage_quantized(x, bits, scaled)
            reference = x_ref / nfft if scaled else x_ref
            snr, evm, maxerr = error_metrics(reference, estimate)
            rows.append((bits, scaled, sat, snr, evm, maxerr))
            print(
                f"bits={bits:2d}, scaled={scaled!s:5s}, sat={sat:3d}, "
                f"SNR={snr:8.4f} dB, EVM={evm:10.6f} %, maxerr={maxerr:.7e}"
            )

    scaled_rows = [r for r in rows if r[1]]
    bits = [r[0] for r in scaled_rows]
    snr = [r[3] for r in scaled_rows]
    evm = [r[4] for r in scaled_rows]
    fig, ax1 = plt.subplots(figsize=(7.5, 4.5))
    ax1.plot(bits, snr, marker="o", label="SNR (dB)")
    ax1.set_xlabel("Word length (bits)")
    ax1.set_ylabel("SNR (dB)")
    ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    ax2.semilogy(bits, evm, marker="s", label="RMS EVM (%)")
    ax2.set_ylabel("RMS EVM (%)")
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [line.get_label() for line in lines], loc="center right")
    fig.tight_layout()
    fig.savefig(OUT / "fixed_point_metrics_regenerated.png", dpi=180)
    plt.close(fig)


def main() -> None:
    np.set_printoptions(suppress=True)
    experiment_dft_fft()
    experiment_growth()
    experiment_ram_trace()
    experiment_fixed_point()
    print(f"Regenerated figures: {OUT}")


if __name__ == "__main__":
    main()
