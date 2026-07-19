"""Run all reproducible simulations included with the updated IEEE paper."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "code" / "consolidated_fft_simulation.py",
    ROOT / "code" / "simulation_8_point_radix.py",
    ROOT / "code" / "ifft_fft_ofdm.py",
]


def main() -> None:
    for script in SCRIPTS:
        print(f"\n=== Running {script.name} ===")
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)
    print("\nAll simulations completed successfully.")


if __name__ == "__main__":
    main()
