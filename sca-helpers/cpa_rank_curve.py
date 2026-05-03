"""Run AES-128 CPA and plot aggregate key-rank curve vs number of traces.

The aggregate curve is the mean rank across all 16 key bytes.
Rank 0 means the correct byte guess is top-1.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Iterable

import numpy as np
import trsfile


SBOX = np.array(
    [
        0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
        0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
        0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
        0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
        0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
        0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
        0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
        0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
        0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
        0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
        0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
        0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
        0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
        0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
        0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
        0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
    ],
    dtype=np.uint8,
)
HW = np.array([bin(v).count("1") for v in range(256)], dtype=np.uint8)
KEY_GUESSES = np.arange(256, dtype=np.uint8)


def _extract_param(trace: object, name: str) -> bytes | None:
    params = getattr(trace, "parameters", None)
    if params is None:
        return None
    try:
        candidate = params[name]
    except Exception:
        return None
    raw = getattr(candidate, "value", candidate)
    try:
        return bytes(raw)
    except Exception:
        return None


def _parse_key_hex(key_hex: str) -> bytes:
    normalized = key_hex.strip().lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]
    if len(normalized) != 32:
        raise ValueError("--key-hex must be exactly 32 hex chars (16 bytes).")
    return bytes.fromhex(normalized)


def _default_output_prefix(trs_path: Path) -> Path:
    return trs_path.with_suffix("").with_name(f"{trs_path.stem}_cpa_rank_curve")


def _build_steps(max_traces: int, step: int) -> list[int]:
    values = list(range(step, max_traces + 1, step))
    if not values or values[-1] != max_traces:
        values.append(max_traces)
    return values


def _compute_tvla_peak_sample(tvla_trs_path: Path, fixed_plaintext: bytes) -> int:
    sum0 = None
    sum1 = None
    sumsq0 = None
    sumsq1 = None
    n0 = 0
    n1 = 0
    with trsfile.open(str(tvla_trs_path), "r") as traceset:
        for trace in traceset:
            pt = _extract_param(trace, "PT")
            if pt is None:
                continue
            samples = np.asarray(trace.samples, dtype=np.float64)
            if samples.size == 0:
                continue
            if sum0 is None:
                sum0 = np.zeros_like(samples)
                sum1 = np.zeros_like(samples)
                sumsq0 = np.zeros_like(samples)
                sumsq1 = np.zeros_like(samples)
            if pt == fixed_plaintext:
                sum0 += samples
                sumsq0 += np.square(samples)
                n0 += 1
            else:
                sum1 += samples
                sumsq1 += np.square(samples)
                n1 += 1
    if sum0 is None or sum1 is None or n0 < 2 or n1 < 2:
        raise ValueError(
            f"TVLA peak selection failed for {tvla_trs_path} "
            f"(group sizes: fixed={n0}, random={n1})."
        )
    mean0 = sum0 / n0
    mean1 = sum1 / n1
    var0 = (sumsq0 - n0 * np.square(mean0)) / (n0 - 1)
    var1 = (sumsq1 - n1 * np.square(mean1)) / (n1 - 1)
    denom = np.sqrt((var0 / n0) + (var1 / n1))
    tvals = np.zeros_like(mean0)
    np.divide(mean0 - mean1, denom, out=tvals, where=denom != 0)
    return int(np.argmax(np.abs(tvals)))


def _rank_of_true_guess(max_abs: np.ndarray, true_key: int) -> int:
    true_score = max_abs[true_key]
    return int(np.sum(max_abs > true_score))


def _compute_rank_curve_incremental(
    traces: np.ndarray,
    leakage_by_byte: list[np.ndarray],
    true_key: bytes,
    trace_steps: list[int],
    chunk_size: int,
) -> tuple[list[float], list[int], list[int]]:
    """Compute rank curve incrementally across steps.

    This avoids re-running CPA from trace 0 at every step and updates
    step-by-step using only newly added traces.
    """
    trace_count, sample_count = traces.shape
    step_count = len(trace_steps)
    if step_count == 0:
        return [], [], []

    # Per-step rank data by key byte.
    ranks_by_step = np.zeros((step_count, 16), dtype=np.int32)

    for byte_index in range(16):
        byte_started = time.time()
        print(f"[info] CPA byte {byte_index + 1}/16 started", flush=True)
        predictions = leakage_by_byte[byte_index].astype(np.float64, copy=False)

        # Precompute prediction running statistics for all requested steps once.
        pred_sum_steps = np.zeros((step_count, 256), dtype=np.float64)
        pred_ss_steps = np.zeros((step_count, 256), dtype=np.float64)
        sum_p = np.zeros(256, dtype=np.float64)
        sum_p2 = np.zeros(256, dtype=np.float64)
        prev_n = 0
        for step_idx, n in enumerate(trace_steps):
            p_block = predictions[prev_n:n]
            sum_p += np.sum(p_block, axis=0, dtype=np.float64)
            sum_p2 += np.einsum("nk,nk->k", p_block, p_block, dtype=np.float64, optimize=True)
            pred_sum_steps[step_idx] = sum_p
            pred_ss = sum_p2 - (sum_p * sum_p) / float(n)
            pred_ss_steps[step_idx] = np.maximum(pred_ss, 0.0)
            prev_n = n

        # Track per-step max absolute correlation over all time samples.
        max_abs_by_step = np.zeros((step_count, 256), dtype=np.float64)

        # Process sample dimension in chunks to keep memory bounded.
        for sample_start in range(0, sample_count, chunk_size):
            sample_end = min(sample_start + chunk_size, sample_count)
            chunk_len = sample_end - sample_start

            sum_t = np.zeros(chunk_len, dtype=np.float64)
            sum_t2 = np.zeros(chunk_len, dtype=np.float64)
            cross = np.zeros((256, chunk_len), dtype=np.float64)

            prev_n = 0
            for step_idx, n in enumerate(trace_steps):
                t_block = traces[prev_n:n, sample_start:sample_end].astype(np.float64, copy=False)
                p_block = predictions[prev_n:n]
                sum_t += np.sum(t_block, axis=0, dtype=np.float64)
                sum_t2 += np.einsum("ns,ns->s", t_block, t_block, dtype=np.float64, optimize=True)
                cross += p_block.T @ t_block

                n_float = float(n)
                numerator = cross - np.outer(pred_sum_steps[step_idx], sum_t) / n_float
                trace_ss = sum_t2 - (sum_t * sum_t) / n_float
                trace_ss = np.maximum(trace_ss, 0.0)
                denominator = np.sqrt(np.outer(pred_ss_steps[step_idx], trace_ss))
                corr = np.divide(
                    numerator,
                    denominator,
                    out=np.zeros_like(numerator),
                    where=denominator != 0,
                )
                chunk_max = np.max(np.abs(corr), axis=1)
                max_abs_by_step[step_idx] = np.maximum(max_abs_by_step[step_idx], chunk_max)
                prev_n = n

        for step_idx in range(step_count):
            ranks_by_step[step_idx, byte_index] = _rank_of_true_guess(
                max_abs_by_step[step_idx],
                true_key[byte_index],
            )
        elapsed_s = time.time() - byte_started
        print(f"[info] CPA byte {byte_index + 1}/16 done in {elapsed_s:.1f}s", flush=True)

    mean_ranks = [float(np.mean(ranks_by_step[i])) for i in range(step_count)]
    worst_ranks = [int(np.max(ranks_by_step[i])) for i in range(step_count)]
    correct_counts = [int(np.sum(ranks_by_step[i] == 0)) for i in range(step_count)]
    return mean_ranks, worst_ranks, correct_counts


def _read_cpa_inputs(
    trs_path: Path,
    max_traces: int | None,
    sample_from: int,
    sample_to: int | None,
) -> tuple[np.ndarray, np.ndarray, bytes]:
    with trsfile.open(str(trs_path), "r") as traceset:
        total_traces = len(traceset)
        if total_traces <= 0:
            raise ValueError(f"No traces in file: {trs_path}")
        use_traces = total_traces if max_traces is None else min(total_traces, max_traces)
        print(f"[info] Loading traces: {use_traces}/{total_traces} from {trs_path}", flush=True)
        first_trace = traceset[0]
        first_samples = np.asarray(first_trace.samples, dtype=np.float32)
        full_sample_count = int(first_samples.shape[0])
        end = full_sample_count if sample_to is None else min(sample_to, full_sample_count)
        if sample_from < 0 or sample_from >= end:
            raise ValueError(f"Invalid sample range [{sample_from}, {end}) for {full_sample_count} samples.")
        out_sample_count = end - sample_from
        traces = np.empty((use_traces, out_sample_count), dtype=np.float32)
        plaintexts = np.empty((use_traces, 16), dtype=np.uint8)

        key = _extract_param(first_trace, "KEY")
        if key is None or len(key) != 16:
            raise ValueError(f"Failed to read KEY parameter from first trace in {trs_path}.")

        for i in range(use_traces):
            trace = traceset[i]
            pt = _extract_param(trace, "PT")
            if pt is None or len(pt) != 16:
                raise ValueError(f"Missing/invalid PT parameter at trace index {i}.")
            samples = np.asarray(trace.samples[sample_from:end], dtype=np.float32)
            if samples.shape[0] != out_sample_count:
                raise ValueError(
                    f"Unexpected sample length at trace index {i}: "
                    f"expected {out_sample_count}, got {samples.shape[0]}."
                )
            plaintexts[i] = np.frombuffer(pt, dtype=np.uint8)
            traces[i] = samples
            if (i + 1) % 500 == 0 or (i + 1) == use_traces:
                print(f"[info] Loaded traces: {i + 1}/{use_traces}", flush=True)
    return traces, plaintexts, key


def _precompute_leakage(plaintexts: np.ndarray) -> list[np.ndarray]:
    leakage_by_byte: list[np.ndarray] = []
    for byte_index in range(16):
        pt_col = plaintexts[:, byte_index][:, None]
        sbox_out = SBOX[np.bitwise_xor(pt_col, KEY_GUESSES[None, :])]
        leakage = HW[sbox_out].astype(np.float32)
        leakage_by_byte.append(leakage)
    return leakage_by_byte


def _write_csv(
    csv_path: Path,
    rows: Iterable[tuple[int, float, int, int]],
) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["traces", "mean_rank", "worst_rank", "correct_bytes"])
        for row in rows:
            writer.writerow(row)


def _save_plot(
    png_path: Path,
    trace_steps: list[int],
    mean_ranks: list[float],
    worst_ranks: list[int],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(trace_steps, mean_ranks, label="Mean Byte Rank", linewidth=2.0)
    ax.plot(trace_steps, worst_ranks, label="Worst-Byte Rank", linewidth=1.5, linestyle="--")
    ax.set_xlabel("Number of Traces")
    ax.set_ylabel("Rank (0 is best)")
    ax.set_title("CPA Aggregate Key-Rank Curve")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(png_path, dpi=180)
    plt.close(fig)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CPA and compute aggregate rank curve.")
    parser.add_argument("--trs", type=Path, required=True, help="CPA trace set (.trs) with PT and KEY params.")
    parser.add_argument(
        "--key-hex",
        type=str,
        default=None,
        help="Optional known 16-byte key in hex. If omitted, KEY from first trace is used.",
    )
    parser.add_argument("--step", type=int, default=25, help="Rank-curve step size in traces (default: 25).")
    parser.add_argument("--max-traces", type=int, default=None, help="Optional trace count cap.")
    parser.add_argument("--sample-from", type=int, default=0, help="Start sample index (inclusive).")
    parser.add_argument("--sample-to", type=int, default=None, help="End sample index (exclusive).")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=2000,
        help="Sample chunk size for correlation computation (default: 2000).",
    )
    parser.add_argument(
        "--tvla-reference-trs",
        type=Path,
        default=None,
        help="Optional TVLA TRS used to auto-select a CPA ROI around max|t|.",
    )
    parser.add_argument(
        "--tvla-fixed-plaintext-hex",
        type=str,
        default="DA39A3EE5E6B4B0D3255BFEF95601890",
        help="Fixed plaintext used in TVLA reference (default matches measurement config).",
    )
    parser.add_argument(
        "--roi-half-width",
        type=int,
        default=1000,
        help="Half-width around TVLA peak for auto ROI if tvla-reference-trs is set (default: 1000).",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=None,
        help="Optional output prefix path (without extension).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.step <= 0:
        raise ValueError("--step must be > 0.")
    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0.")

    trs_path = args.trs.resolve()
    if not trs_path.exists():
        raise FileNotFoundError(f"TRS file not found: {trs_path}")

    sample_from = int(args.sample_from)
    sample_to = args.sample_to

    if args.tvla_reference_trs is not None and args.sample_to is None:
        tvla_path = args.tvla_reference_trs.resolve()
        if not tvla_path.exists():
            raise FileNotFoundError(f"TVLA reference TRS not found: {tvla_path}")
        fixed_pt = _parse_key_hex(args.tvla_fixed_plaintext_hex)
        peak = _compute_tvla_peak_sample(tvla_path, fixed_pt)
        sample_from = max(0, peak - args.roi_half_width)
        sample_to = peak + args.roi_half_width + 1
        print(
            f"[info] Auto ROI from TVLA peak: peak={peak}, "
            f"window=[{sample_from}, {sample_to})"
        )

    traces, plaintexts, key_from_trs = _read_cpa_inputs(
        trs_path=trs_path,
        max_traces=args.max_traces,
        sample_from=sample_from,
        sample_to=sample_to,
    )
    true_key = _parse_key_hex(args.key_hex) if args.key_hex else key_from_trs
    if len(true_key) != 16:
        raise ValueError("True key must be exactly 16 bytes.")

    if traces.shape[1] > 20_000:
        print(
            f"[warn] Large sample window ({traces.shape[1]} points). "
            f"Consider --tvla-reference-trs or --sample-from/--sample-to for faster runtime."
        )
    print(
        f"[info] Using incremental CPA engine | traces={traces.shape[0]} "
        f"| samples={traces.shape[1]} | step={args.step} | chunk_size={args.chunk_size}"
    )

    leakage_by_byte = _precompute_leakage(plaintexts)
    trace_steps = _build_steps(traces.shape[0], args.step)
    mean_ranks, worst_ranks, correct_counts = _compute_rank_curve_incremental(
        traces=traces,
        leakage_by_byte=leakage_by_byte,
        true_key=true_key,
        trace_steps=trace_steps,
        chunk_size=args.chunk_size,
    )

    for n, mean_rank, worst_rank, correct_bytes in zip(trace_steps, mean_ranks, worst_ranks, correct_counts):
        print(
            f"[progress] traces={n:5d} | mean_rank={mean_rank:7.3f} "
            f"| worst_rank={worst_rank:3d} | correct_bytes={correct_bytes:2d}/16"
        )

    output_prefix = args.output_prefix.resolve() if args.output_prefix else _default_output_prefix(trs_path)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_prefix.with_suffix(".csv")
    png_path = output_prefix.with_suffix(".png")
    meta_path = output_prefix.with_suffix(".json")

    rows = list(zip(trace_steps, mean_ranks, worst_ranks, correct_counts))
    _write_csv(csv_path, rows)
    _save_plot(png_path, trace_steps, mean_ranks, worst_ranks)

    metadata = {
        "trs_path": str(trs_path),
        "trace_count_used": int(traces.shape[0]),
        "sample_from": int(sample_from),
        "sample_to": int(sample_from + traces.shape[1]),
        "sample_count": int(traces.shape[1]),
        "step": int(args.step),
        "chunk_size": int(args.chunk_size),
        "true_key_hex": true_key.hex().upper(),
        "tvla_reference_trs": None if args.tvla_reference_trs is None else str(args.tvla_reference_trs.resolve()),
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"[done] CSV:  {csv_path}")
    print(f"[done] Plot: {png_path}")
    print(f"[done] Meta: {meta_path}")


if __name__ == "__main__":
    main()
