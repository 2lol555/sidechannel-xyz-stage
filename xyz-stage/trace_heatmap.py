"""Trace heatmap rendering utilities."""

from pathlib import Path
from typing import Callable, List, Optional, Tuple

from side_channel_types import ScanResults


TraceMetricFn = Callable[["np.ndarray"], float]


def absolute_strength_metric(samples: "np.ndarray") -> float:
    """Absolute trace strength metric: mean(abs(samples))."""
    import numpy as np

    return float(np.mean(np.abs(samples)))


def _load_first_trace_samples(trace_path: Path) -> Optional["np.ndarray"]:
    import numpy as np
    import trsfile

    with trsfile.open(str(trace_path), "r") as traceset:
        if len(traceset) == 0:
            return None
        return np.asarray(traceset[0].samples, dtype=np.float32)


def compute_trace_score(trace_path: Path, metric_fn: TraceMetricFn = absolute_strength_metric) -> float:
    """Compute a scalar score from a trace using metric_fn."""
    import numpy as np

    samples = _load_first_trace_samples(trace_path)
    if samples is None or samples.size == 0:
        raise ValueError(f"Trace has no samples: {trace_path}")

    score = float(metric_fn(samples))
    if not np.isfinite(score):
        raise ValueError(f"Metric returned non-finite value for: {trace_path}")
    return score


def _build_axes(results: ScanResults) -> Tuple[List[float], List[float]]:
    x_values = sorted({pos[0] for pos in results.keys()})
    y_values = sorted({pos[1] for pos in results.keys()})
    return x_values, y_values


def build_heatmap_grid(
    results: ScanResults,
    metric_fn: TraceMetricFn = absolute_strength_metric,
) -> Tuple["np.ndarray", List[float], List[float], int, dict]:
    """Map per-point trace scores to a 2D grid (NaN where unavailable)."""
    import numpy as np

    x_values, y_values = _build_axes(results)
    if not x_values or not y_values:
        raise ValueError("No scan points available for heatmap.")

    grid = np.full((len(y_values), len(x_values)), np.nan, dtype=np.float64)
    x_to_col = {x: i for i, x in enumerate(x_values)}
    y_to_row = {y: i for i, y in enumerate(y_values)}

    scored_points = 0
    point_to_index = {point: idx for idx, point in enumerate(results.keys())}
    for (x, y), point_res in results.items():
        if not point_res.ok or not point_res.trace_path:
            continue

        trace_path = Path(point_res.trace_path)
        if not trace_path.exists():
            continue

        try:
            score = compute_trace_score(trace_path, metric_fn=metric_fn)
        except Exception:
            continue

        row = y_to_row.get(y)
        col = x_to_col.get(x)
        if row is None or col is None:
            continue

        grid[row, col] = score
        scored_points += 1

    return grid, x_values, y_values, scored_points, point_to_index


def render_trace_metric_heatmap(
    results: ScanResults,
    metric_fn: TraceMetricFn = absolute_strength_metric,
    metric_name: str = "absolute_strength",
) -> None:
    """Render a heatmap of metric scores for scanned points."""
    import numpy as np
    import matplotlib.pyplot as plt

    grid, x_values, y_values, scored_points, point_to_index = build_heatmap_grid(results, metric_fn=metric_fn)

    finite_values = grid[np.isfinite(grid)]
    if finite_values.size == 0:
        raise ValueError("No valid trace scores available for heatmap.")

    fig_w = min(16.0, max(8.0, len(x_values) * 0.5))
    fig_h = min(12.0, max(6.0, len(y_values) * 0.5))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="#d9d9d9")
    image = ax.imshow(grid, origin="upper", aspect="auto", cmap=cmap)

    # Overlay scan-point indices to match evaluation-phase "goto N" numbering.
    x_to_col = {x: i for i, x in enumerate(x_values)}
    y_to_row = {y: i for i, y in enumerate(y_values)}
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
        f"Trace Heatmap ({metric_name}) | scored={scored_points}/{len(results)} "
        f"| min={min_score:.4f}, max={max_score:.4f}"
    )

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label(f"{metric_name} score")

    fig.tight_layout()
    plt.show(block=False)
    plt.pause(0.001)
