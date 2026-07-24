#!/usr/bin/env python3
"""Collect model, XSim, Vivado, and SPICE evidence into one manifest."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
VIVADO = REPORTS / "vivado"
REFERENCE = REPORTS / "reference"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def key_values(path: Path) -> dict[str, str | int | float]:
    values: dict[str, str | int | float] = {}
    for line in read_text(path).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if re.fullmatch(r"-?\d+", value):
            values[key] = int(value)
        elif re.fullmatch(r"-?(?:\d+\.\d*|\d*\.\d+)", value):
            values[key] = float(value)
        else:
            values[key] = value
    return values


def table_resource(text: str, labels: tuple[str, ...]) -> dict[str, float | int]:
    normalized = tuple(label.lower() for label in labels)
    for line in text.splitlines():
        if "|" not in line:
            continue
        fields = [field.strip() for field in line.strip().strip("|").split("|")]
        if len(fields) < 2:
            continue
        label = fields[0].lower().rstrip("*")
        if label not in normalized:
            continue
        numeric = []
        for field in fields[1:]:
            token = field.replace(",", "").replace("%", "")
            try:
                numeric.append(float(token))
            except ValueError:
                numeric.append(float("nan"))
        result: dict[str, float | int] = {}
        if numeric and not math_is_nan(numeric[0]):
            result["used"] = int(numeric[0])
        # Vivado 2022.2 reports:
        # Used | Fixed | Prohibited | Available | Util%.
        # Older variants may omit one of the middle columns, so take the last
        # two numeric fields rather than relying on a fixed early index.
        if len(numeric) >= 3 and not math_is_nan(numeric[-2]):
            result["available"] = int(numeric[-2])
        if len(numeric) >= 2 and not math_is_nan(numeric[-1]):
            result["utilization_percent"] = numeric[-1]
        return result
    raise ValueError(f"resource row not found: {labels}")


def math_is_nan(value: float) -> bool:
    return value != value


def parse_utilization(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return {
        "slice_luts": table_resource(text, ("Slice LUTs", "CLB LUTs")),
        "lut_as_logic": table_resource(text, ("LUT as Logic",)),
        "slice_registers": table_resource(
            text, ("Slice Registers", "CLB Registers")
        ),
        "block_ram_tiles": table_resource(text, ("Block RAM Tile",)),
        "dsps": table_resource(text, ("DSPs", "DSP48E1 only")),
        "bonded_iob": table_resource(text, ("Bonded IOB",)),
    }


def parse_wns(text: str) -> float:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "WNS(ns)" not in line or "TNS(ns)" not in line:
            continue
        for candidate in lines[index + 1 : index + 8]:
            fields = candidate.split()
            if not fields:
                continue
            try:
                return float(fields[0])
            except ValueError:
                continue
    match = re.search(r"Slack\s+\((?:MET|VIOLATED)\)\s*:\s*(-?[0-9.]+)ns", text)
    if match:
        return float(match.group(1))
    raise ValueError("WNS/slack was not found")


def parse_timing(summary_path: Path, paths_path: Path, period_ns: float) -> dict[str, Any]:
    summary = read_text(summary_path)
    paths = read_text(paths_path)
    wns = parse_wns(summary)
    delay_match = re.search(
        r"Data Path Delay:\s*([0-9.]+)ns"
        r"(?:\s*\(logic\s*([0-9.]+)ns.*?route\s*([0-9.]+)ns\))?",
        paths,
    )
    effective_period = period_ns - wns
    result: dict[str, Any] = {
        "constraint_period_ns": period_ns,
        "constraint_frequency_mhz": 1000.0 / period_ns,
        "worst_negative_slack_ns": wns,
        "timing_met": wns >= 0.0,
        "estimated_fmax_mhz": (
            1000.0 / effective_period if effective_period > 0.0 else None
        ),
    }
    if delay_match:
        result["critical_data_path_delay_ns"] = float(delay_match.group(1))
        if delay_match.group(2):
            result["critical_logic_delay_ns"] = float(delay_match.group(2))
        if delay_match.group(3):
            result["critical_route_delay_ns"] = float(delay_match.group(3))
    return result


def parse_power(path: Path, provenance_path: Path) -> dict[str, Any]:
    text = read_text(path)

    def search(pattern: str) -> float | None:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return float(match.group(1)) if match else None

    result: dict[str, Any] = {
        "total_on_chip_power_w": search(
            r"Total On-Chip Power\s*\(W\)\s*\|\s*([0-9.]+)"
        ),
        "dynamic_power_w": search(
            r"^\s*\|?\s*Dynamic\s*\(W\)\s*\|\s*([0-9.]+)"
        ),
        "device_static_power_w": search(
            r"Device Static\s*\(W\)\s*\|\s*([0-9.]+)"
        ),
    }
    confidence = re.search(
        r"\|\s*Confidence Level\s*\|\s*([A-Za-z]+)", text, re.IGNORECASE
    )
    if confidence:
        result["confidence_level"] = confidence.group(1)
    matched = re.search(
        r"\|\s*Design Nets Matched\s*\|\s*([0-9.]+)%"
        r"\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)",
        text,
        re.IGNORECASE,
    )
    if matched:
        result["activity_net_match_percent"] = float(matched.group(1))
        result["activity_nets_matched"] = int(matched.group(2))
        result["activity_nets_total"] = int(matched.group(3))
    if provenance_path.exists():
        result["provenance"] = key_values(provenance_path)
    return result


def reference_simulation() -> dict[str, Any] | None:
    candidates = (
        REFERENCE / "rtl_cxxrtl_summary.txt",
        ROOT.parent / "FFT8_RTL_ASIC_Paper" / "reports" / "rtl_verification_summary.txt",
    )
    for path in candidates:
        if path.exists():
            data = key_values(path)
            data["summary_path"] = str(path.relative_to(ROOT.parent))
            return data
    return None


def attribute_is_true(value: Any) -> bool:
    if value is True or value == 1:
        return True
    if isinstance(value, str):
        try:
            return int(value, 2) != 0
        except ValueError:
            return value.lower() in {"true", "yes"}
    return False


def primitive_counts(netlist_path: Path, top: str) -> Counter[str]:
    """Flatten user hierarchy while stopping at technology primitives."""
    design = json.loads(read_text(netlist_path))
    modules = design["modules"]
    if top not in modules:
        raise KeyError(f"top module {top!r} not found in {netlist_path}")

    def walk(module_name: str, active: tuple[str, ...]) -> Counter[str]:
        if module_name in active:
            raise ValueError(f"recursive module hierarchy at {module_name}")
        result: Counter[str] = Counter()
        for cell in modules[module_name].get("cells", {}).values():
            cell_type = cell["type"]
            target = modules.get(cell_type)
            is_blackbox = target is not None and attribute_is_true(
                target.get("attributes", {}).get("blackbox", False)
            )
            if target is not None and not is_blackbox:
                result.update(walk(cell_type, active + (module_name,)))
            else:
                result[cell_type] += 1
        return result

    return walk(top, ())


def mapping_summary(netlist_path: Path, top: str) -> dict[str, Any]:
    counts = primitive_counts(netlist_path, top)
    lut_types = ("LUT1", "LUT2", "LUT3", "LUT4", "LUT5", "LUT6", "LUT6_2")
    register_types = tuple(
        cell_type
        for cell_type in counts
        if re.fullmatch(r"FD[A-Z0-9_]*", cell_type)
    )
    return {
        "top": top,
        "mapped_lut_primitives": sum(counts[name] for name in lut_types),
        "register_primitives": sum(counts[name] for name in register_types),
        "carry4_primitives": counts["CARRY4"],
        "dsp48e1_primitives": counts["DSP48E1"],
        "muxf7_primitives": counts["MUXF7"],
        "block_ram_primitives": sum(
            count for name, count in counts.items() if name.startswith("RAMB")
        ),
        "primitive_counts": dict(sorted(counts.items())),
    }


def reference_mapping() -> dict[str, Any] | None:
    optimized_json = ROOT / "build" / "reference" / "fft8_optimized_xc7.json"
    baseline_json = ROOT / "build" / "reference" / "fft8_baseline_xc7.json"
    if not optimized_json.exists() or not baseline_json.exists():
        return None

    version = "not recorded"
    optimized_log = REFERENCE / "yosys_xc7_optimized.log"
    if optimized_log.exists():
        match = re.search(r"\bYosys\s+([0-9.]+)", read_text(optimized_log))
        if match:
            version = match.group(1)

    return {
        "result": "PASS",
        "tool": "Yosys",
        "version": version,
        "family": "Xilinx 7-series technology mapping",
        "placement_and_routing": "not performed",
        "baseline": mapping_summary(baseline_json, "fft8_top_baseline"),
        "optimized": mapping_summary(optimized_json, "fft8_top"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    model_path = REPORTS / "model_summary.json"
    if not model_path.exists():
        raise FileNotFoundError("run model/fft8_fixed_model.py first")
    model = json.loads(read_text(model_path))
    consistency_path = REFERENCE / "model_consistency.json"
    consistency = (
        json.loads(read_text(consistency_path)) if consistency_path.exists() else None
    )
    spice_path = REFERENCE / "spice_summary.json"
    spice = json.loads(read_text(spice_path)) if spice_path.exists() else None

    metadata_path = VIVADO / "run_metadata.txt"
    metadata = key_values(metadata_path) if metadata_path.exists() else {
        "target_part": "xc7a35tcpg236-1",
        "target_period_ns": 25.0,
        "flow": "Vivado project mode",
    }
    period_ns = float(metadata.get("target_period_ns", 25.0))

    ofdm_path = REPORTS / "ofdm_loopback_summary.json"
    if not ofdm_path.exists():
        raise FileNotFoundError("run model/ofdm_fft8_loopback.py first")
    ofdm = json.loads(read_text(ofdm_path))

    required = {
        "behavioral": VIVADO / "xsim_behavioral_summary.txt",
        "post_synth": VIVADO / "xsim_post_synth_summary.txt",
        "post_impl_timing": VIVADO / "xsim_post_impl_timing_summary.txt",
        "synth_utilization": VIVADO / "synth_utilization.rpt",
        "synth_baseline_utilization": VIVADO / "synth_baseline_utilization.rpt",
        "impl_utilization": VIVADO / "impl_utilization.rpt",
        "impl_timing_summary": VIVADO / "impl_timing_summary.rpt",
        "impl_timing_paths": VIVADO / "impl_timing_paths.rpt",
        "impl_power": VIVADO / "impl_power.rpt",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    vivado_completed = not missing

    vivado: dict[str, Any] = {
        "status": "completed" if vivado_completed else "not_executed",
        "metadata": metadata,
        "missing_evidence": missing,
    }
    if vivado_completed:
        vivado["behavioral_simulation"] = key_values(required["behavioral"])
        vivado["post_synthesis_simulation"] = key_values(required["post_synth"])
        vivado["post_implementation_timing_simulation"] = key_values(
            required["post_impl_timing"]
        )
        vivado["synthesis"] = {
            "optimized_utilization": parse_utilization(
                required["synth_utilization"]
            ),
            "baseline_utilization": parse_utilization(
                required["synth_baseline_utilization"]
            ),
        }
        vivado["implementation"] = {
            "utilization": parse_utilization(required["impl_utilization"]),
            "timing": parse_timing(
                required["impl_timing_summary"],
                required["impl_timing_paths"],
                period_ns,
            ),
            "power": parse_power(
                required["impl_power"], VIVADO / "power_provenance.txt"
            ),
        }
        fmax = vivado["implementation"]["timing"]["estimated_fmax_mhz"]
        if fmax is not None:
            transforms = fmax * 1e6 / 29.0
            vivado["implementation"]["derived"] = {
                "minimum_initiation_interval_cycles": 29,
                "transforms_per_second_at_estimated_fmax": transforms,
                "complex_samples_per_second_at_estimated_fmax": transforms * 8,
            }

    manifest = {
        "design": {
            "algorithm": "8-point radix-2 DIT FFT",
            "arithmetic": "signed Q1.15",
            "architecture": "single reused butterfly, in-place register file",
            "output_normalization": "FFT/8",
            "input_output_order": "natural/natural",
        },
        "fixed_point": model,
        "ofdm_integration": ofdm,
        "independent_model_tests": consistency,
        "independent_rtl_crosscheck": reference_simulation(),
        "reference_xilinx_mapping": reference_mapping(),
        "vivado": vivado,
        "transistor_level": spice,
        "evidence_boundary": {
            "vivado_claims_enabled": vivado_completed,
            "vivado_metrics_are_never_substituted_with_yosys": True,
            "transistor_schematic_spice": (
                "completed with generic Level-1 models" if spice else "not included"
            ),
            "foundry_pdk_drc_lvs_extraction": "not performed",
            "fabricated_silicon": "not claimed",
        },
    }
    output = REPORTS / "results_manifest.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"manifest={output.relative_to(ROOT)} vivado_status={vivado['status']} "
        f"missing={','.join(missing) if missing else 'none'}"
    )
    if args.require_complete and not vivado_completed:
        raise SystemExit(
            "Vivado evidence is incomplete; refusing to enable Vivado paper claims"
        )


if __name__ == "__main__":
    main()
