#!/usr/bin/env python3
"""Fail if RTL/model/Vivado evidence and paper-facing data disagree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "reports" / "results_manifest.json"
MACROS_PATH = ROOT / "paper" / "generated" / "results_macros.tex"
PAPER_PATH = ROOT / "paper" / "main.tex"


def require_equal(name: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(f"{name}: {actual!r} != {expected!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-vivado", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    fixed = manifest["fixed_point"]
    memory_path = ROOT / "testvectors" / "fft8_vectors.mem"
    memory_digest = hashlib.sha256(memory_path.read_bytes()).hexdigest()
    require_equal("vector SHA-256", memory_digest, fixed["xsim_memory"]["sha256"])
    require_equal("vector frames", fixed["verification_vectors"]["frames"], 2009)
    require_equal("XSim memory frames", fixed["xsim_memory"]["frames"], 2009)
    require_equal("XSim words/frame", fixed["xsim_memory"]["words_per_frame"], 32)

    ofdm = manifest["ofdm_integration"]
    require_equal("OFDM integration result", ofdm["result"], "PASS")
    require_equal("OFDM frames", ofdm["frames"], 10000)
    require_equal("OFDM total bits", ofdm["total_bits"], 160000)
    require_equal("OFDM bit errors", ofdm["bit_errors"], 0)
    require_equal("OFDM cyclic prefix", ofdm["cyclic_prefix_samples"], 2)
    require_equal("OFDM TX saturations", ofdm["tx_saturations"], 0)
    require_equal("OFDM RX saturations", ofdm["rx_saturations"], 0)

    reference = manifest.get("independent_rtl_crosscheck")
    if reference:
        require_equal("reference result", reference["result"], "PASS")
        require_equal("reference frames", reference["frames"], 2009)
        require_equal("reference outputs", reference["outputs_checked"], 16072)
        require_equal("reference mismatches", reference["mismatches"], 0)
        require_equal("reference assertions", reference["assertion_failures"], 0)
        require_equal(
            "reference latency first",
            reference["latency_start_to_first_output_cycles"],
            20,
        )
        require_equal(
            "reference latency done",
            reference["latency_start_to_done_cycles"],
            28,
        )
        require_equal("W0 coverage", reference["twiddle_W0_uses"], 2009 * 7)
        require_equal("W1 coverage", reference["twiddle_W1_uses"], 2009)
        require_equal("W2 coverage", reference["twiddle_W2_uses"], 2009 * 3)
        require_equal("W3 coverage", reference["twiddle_W3_uses"], 2009)
        for stage in range(3):
            require_equal(
                f"stage {stage} coverage", reference[f"stage{stage}_cycles"], 2009 * 4
            )

    mapping = manifest.get("reference_xilinx_mapping")
    if mapping:
        require_equal("reference mapping result", mapping["result"], "PASS")
        baseline = mapping["baseline"]
        optimized = mapping["optimized"]
        if int(optimized["dsp48e1_primitives"]) >= int(
            baseline["dsp48e1_primitives"]
        ):
            raise AssertionError("optimized twiddle did not reduce DSP48E1 count")
        require_equal(
            "reference mapping register parity",
            optimized["register_primitives"],
            baseline["register_primitives"],
        )
        for variant_name, variant in (
            ("baseline", baseline),
            ("optimized", optimized),
        ):
            if int(variant["mapped_lut_primitives"]) <= 0:
                raise AssertionError(f"{variant_name} mapping has no LUT primitives")

    vivado = manifest["vivado"]
    completed = vivado["status"] == "completed"
    if args.require_vivado and not completed:
        raise AssertionError("Vivado reports are required but not present")
    if completed:
        require_equal(
            "target period",
            float(vivado["metadata"]["target_period_ns"]),
            25.0,
        )
        behavioral = vivado["behavioral_simulation"]
        require_equal("XSim behavioral result", behavioral["result"], "PASS")
        for field in (
            "frames",
            "outputs_checked",
            "mismatches",
            "assertion_failures",
            "overflow_frames",
            "latency_start_to_first_output_cycles",
            "latency_start_to_done_cycles",
            "twiddle_W0_uses",
            "twiddle_W1_uses",
            "twiddle_W2_uses",
            "twiddle_W3_uses",
            "stage0_cycles",
            "stage1_cycles",
            "stage2_cycles",
        ):
            if reference:
                require_equal(f"XSim/reference {field}", behavioral[field], reference[field])
        require_equal(
            "post-synthesis result",
            vivado["post_synthesis_simulation"]["result"],
            "PASS",
        )
        require_equal(
            "post-synthesis frames",
            vivado["post_synthesis_simulation"]["frames"],
            2009,
        )
        require_equal(
            "post-synthesis mismatches",
            vivado["post_synthesis_simulation"]["mismatches"],
            0,
        )
        require_equal(
            "post-implementation result",
            vivado["post_implementation_timing_simulation"]["result"],
            "PASS",
        )
        require_equal(
            "post-implementation directed frames",
            vivado["post_implementation_timing_simulation"]["frames"],
            11,
        )
        require_equal(
            "post-implementation mismatches",
            vivado["post_implementation_timing_simulation"]["mismatches"],
            0,
        )
        require_equal(
            "post-route timing closure",
            vivado["implementation"]["timing"]["timing_met"],
            True,
        )
        synth = vivado["synthesis"]
        if (
            int(synth["optimized_utilization"]["dsps"]["used"])
            >= int(synth["baseline_utilization"]["dsps"]["used"])
        ):
            raise AssertionError("Vivado optimized twiddle did not reduce DSP use")
        for scope_name, resources in (
            ("optimized synthesis", synth["optimized_utilization"]),
            ("baseline synthesis", synth["baseline_utilization"]),
            ("implementation", vivado["implementation"]["utilization"]),
        ):
            for resource_name in (
                "slice_luts",
                "slice_registers",
                "dsps",
                "block_ram_tiles",
                "bonded_iob",
            ):
                resource = resources[resource_name]
                if int(resource["available"]) < int(resource["used"]):
                    raise AssertionError(
                        f"{scope_name} {resource_name}: available < used"
                    )
        power = vivado["implementation"]["power"]
        for field in (
            "confidence_level",
            "activity_net_match_percent",
            "activity_nets_matched",
            "activity_nets_total",
        ):
            if field not in power:
                raise AssertionError(f"power evidence missing {field}")

    paper = PAPER_PATH.read_text(encoding="utf-8")
    stale_claims = (
        "iCE40HX8K",
        "SB_MAC16",
        "nextpnr",
        "23.08",
        "2,259 of 7,680",
    )
    found_stale = [token for token in stale_claims if token in paper]
    if found_stale:
        raise AssertionError(f"stale iCE40 claims remain in paper: {found_stale}")

    required_macros = (
        r"\RtlFrames",
        r"\RtlOutputs",
        r"\SqnrSixteen",
        r"\SynthDsps",
        r"\ImplLuts",
        r"\WnsNs",
        r"\VivadoFmaxMHz",
        r"\OfdmBer",
        r"\VivadoPowerConfidence",
    )
    missing_macros = [name for name in required_macros if name not in paper]
    if missing_macros:
        raise AssertionError(f"paper does not consume result macros: {missing_macros}")

    macros = MACROS_PATH.read_text(encoding="utf-8")
    if completed and "NOT EXECUTED" in macros:
        raise AssertionError("completed Vivado flow still renders NOT EXECUTED")
    if not completed and not re.search(
        r"\\newcommand\{\\VivadoStatus\}\{NOT EXECUTED\}", macros
    ):
        raise AssertionError("pre-Vivado draft does not disclose missing execution")

    result = {
        "result": "PASS",
        "vivado_status": vivado["status"],
        "vector_sha256": memory_digest,
        "paper_stale_claims": [],
        "paper_macro_source": str(MACROS_PATH.relative_to(ROOT)),
    }
    output = ROOT / "reports" / "consistency_audit.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"PASS: audit vivado_status={vivado['status']} vector_sha256={memory_digest}")


if __name__ == "__main__":
    main()
