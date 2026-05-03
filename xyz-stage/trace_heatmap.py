"""TVLA heatmap rendering utilities."""

from pathlib import Path
from typing import List, Optional, Tuple

from Configuration.measurement import MEASUREMENT_CONFIG
from side_channel_types import ScanResults


def _extract_plaintext(trace: "object") -> Optional[bytes]:
    params = getattr(trace, "parameters", None)
    if params is None:
        return None

    candidate = None
    for key_name in ("PT", "PlainText", "PLAINTEXT"):
        try:
            candidate = params[key_name]
            break
        except Exception:
            candidate = None

    if candidate is None:
        return None
    raw_value = getattr(candidate, "value", candidate)
    try:
        return bytes(raw_value)
    except Exception:
        return None


def compute_tvla_max_abs_t(trace_path: Path, fixed_plaintext: bytes) -> float:
    """Compute max(abs(t)) for fixed-vs-random groups in one TRS file."""
    import numpy as np
    import trsfile

    group_fixed: list[np.ndarray] = []
    group_random: list[np.ndarray] = []

    with trsfile.open(str(trace_path), "r") as traceset:
        for trace in traceset:
            plaintext = _extract_plaintext(trace)
            if plaintext is None:
                continue
            samples = np.asarray(trace.samples, dtype=np.float64)
            if samples.size == 0:
                continue
            if plaintext == fixed_plaintext:
                group_fixed.append(samples)
            else:
                group_random.append(samples)

    if len(group_fixed) < 2 or len(group_random) < 2:
        raise ValueError(
            f"Not enough TVLA traces in groups for {trace_path}: "
            f"fixed={len(group_fixed)} random={len(group_random)}"
        )

    fixed_arr = np.vstack(group_fixed)
    random_arr = np.vstack(group_random)

    fixed_mean = np.mean(fixed_arr, axis=0)
    random_mean = np.mean(random_arr, axis=0)
    fixed_var = np.var(fixed_arr, axis=0, ddof=1)
    random_var = np.var(random_arr, axis=0, ddof=1)

    denominator = np.sqrt((fixed_var / fixed_arr.shape[0]) + (random_var / random_arr.shape[0]))
    t_values = np.zeros_like(fixed_mean, dtype=np.float64)
    np.divide(
        fixed_mean - random_mean,
        denominator,
        out=t_values,
        where=denominator != 0,
    )
    max_abs_t = float(np.max(np.abs(t_values)))
    if not np.isfinite(max_abs_t):
        raise ValueError(f"Non-finite TVLA score for {trace_path}")
    return max_abs_t


def _build_axes(results: ScanResults) -> Tuple[List[float], List[float]]:
    x_values = sorted({pos[0] for pos in results.keys()})
    y_values = sorted({pos[1] for pos in results.keys()})
    return x_values, y_values


def render_trace_metric_heatmap(results: ScanResults, threshold: float = 4.5) -> None:
    """Render TVLA heatmap over scan points using max(abs(t))."""
    import numpy as np
    import matplotlib.pyplot as plt

    fixed_plaintext = MEASUREMENT_CONFIG.target.tvla_fixed_plaintext
    x_values, y_values = _build_axes(results)
    if not x_values or not y_values:
        raise ValueError("No scan points available for heatmap.")

    grid = np.full((len(y_values), len(x_values)), np.nan, dtype=np.float64)
    x_to_col = {x: i for i, x in enumerate(x_values)}
    y_to_row = {y: i for i, y in enumerate(y_values)}
    point_to_index = {point: idx for idx, point in enumerate(results.keys())}

    scored_points = 0
    leaking_points = 0
    for (x, y), point_res in results.items():
        if not point_res.ok or not point_res.trace_path:
            continue

        trace_path = Path(point_res.trace_path)
        if not trace_path.exists():
            continue

        try:
            tvla_score = compute_tvla_max_abs_t(trace_path, fixed_plaintext=fixed_plaintext)
        except Exception:
            continue

        row = y_to_row.get(y)
        col = x_to_col.get(x)
        if row is None or col is None:
            continue

        grid[row, col] = tvla_score
        scored_points += 1
        if tvla_score > threshold:
            leaking_points += 1

    finite_values = grid[np.isfinite(grid)]
    if finite_values.size == 0:
        raise ValueError("No valid TVLA scores available for heatmap.")

    fig_w = min(16.0, max(8.0, len(x_values) * 0.5))
    fig_h = min(12.0, max(6.0, len(y_values) * 0.5))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="#d9d9d9")
    image = ax.imshow(grid, origin="upper", aspect="auto", cmap=cmap)

    for point, idx in point_to_index.items():
        x, y = point
        col = x_to_col.get(x)
        row = y_to_row.get(y)
        if col is None or row is None:
            continue
        ax.text(
            col,
            row,
            str(idx),
            ha="center",
            va="center",
            fontsize=6,
            color="#111111",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "alpha": 0.55, "edgecolor": "none"},
        )

    x_tick_step = max(1, len(x_values) // 10)
    y_tick_step = max(1, len(y_values) // 10)
    x_tick_idx = list(range(0, len(x_values), x_tick_step))
    y_tick_idx = list(range(0, len(y_values), y_tick_step))

    ax.set_xticks(x_tick_idx)
    ax.set_yticks(y_tick_idx)
    ax.set_xticklabels([f"{x_values[i]:.2f}" for i in x_tick_idx], rotation=45, ha="right")
    ax.set_yticklabels([f"{y_values[i]:.2f}" for i in y_tick_idx])
    ax.set_xlabel("X position (mm)")
    ax.set_ylabel("Y position (mm)")

    min_score = float(np.min(finite_values))
    max_score = float(np.max(finite_values))
    ax.set_title(
        f"TVLA Heatmap (max|t|) | scored={scored_points}/{len(results)} "
        f"| leaking>{threshold:.1f}: {leaking_points} "
        f"| min={min_score:.3f}, max={max_score:.3f}"
    )

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("max(|t|)")

    fig.tight_layout()
    plt.show(block=False)
    plt.pause(0.001)
