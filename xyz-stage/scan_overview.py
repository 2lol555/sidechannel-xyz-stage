"""Generate a grid overview image from per-point scan traces."""

from pathlib import Path
from typing import Optional

from logger import info, success, warning
from scan import ScanContext


def _load_trace_samples(trace_path: Path, max_samples: int = 2000):
    import numpy as np
    import trsfile

    with trsfile.open(str(trace_path), "r") as traceset:
        if len(traceset) == 0:
            return None
        samples = np.asarray(traceset[0].samples, dtype=np.float32)

    if samples.size == 0:
        return None
    if samples.size > max_samples:
        step = max(1, samples.size // max_samples)
        samples = samples[::step]
    return samples


def _build_axis_values(scan_ctx: ScanContext):
    x_values = sorted({pos[0] for pos in scan_ctx.positions})
    y_values = sorted({pos[1] for pos in scan_ctx.positions})
    return x_values, y_values


def generate_scan_overview(scan_ctx: ScanContext) -> Optional[Path]:
    """Create and save a grid image where each cell contains one point trace."""
    if not scan_ctx.payload_output_folder:
        warning("No payload output folder available; skipping scan overview image.")
        return None

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        warning(f"matplotlib not available; skipping scan overview image: {exc}")
        return None

    x_values, y_values = _build_axis_values(scan_ctx)
    if not x_values or not y_values:
        warning("No scan positions available; skipping scan overview image.")
        return None

    ncols = len(x_values)
    nrows = len(y_values)
    x_to_col = {x: i for i, x in enumerate(x_values)}
    y_to_row = {y: i for i, y in enumerate(y_values)}

    fig_w = min(36.0, max(10.0, ncols * 1.2))
    fig_h = min(36.0, max(10.0, nrows * 1.2))
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(fig_w, fig_h), squeeze=False)

    for row in range(nrows):
        for col in range(ncols):
            ax = axes[row][col]
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_facecolor("#f6f6f6")

    rendered = 0
    point_to_index = {point: idx for idx, point in enumerate(scan_ctx.results.keys())}
    for (x, y), point_res in scan_ctx.results.items():
        col = x_to_col.get(x)
        row = y_to_row.get(y)
        if col is None or row is None:
            continue
        ax = axes[row][col]
        ax.set_facecolor("#ffffff" if point_res.ok else "#ffe8e8")

        if point_res.trace_path:
            trace_path = Path(point_res.trace_path)
            if trace_path.exists():
                try:
                    samples = _load_trace_samples(trace_path)
                    if samples is not None:
                        ax.plot(samples, linewidth=0.6, color="#1f77b4")
                        rendered += 1
                except Exception:
                    ax.text(0.5, 0.5, "ERR", ha="center", va="center", fontsize=6, color="#a33")

        goto_index = point_to_index.get((x, y))
        if goto_index is not None:
            ax.text(0.02, 0.98, f"#{goto_index}", transform=ax.transAxes, ha="left", va="top", fontsize=7)
        ax.text(0.5, 0.03, f"{x:.1f},{y:.1f}", transform=ax.transAxes, ha="center", va="bottom", fontsize=6)

    for col, x in enumerate(x_values):
        axes[0][col].set_title(f"X={x:.1f}", fontsize=7)
    for row, y in enumerate(y_values):
        axes[row][0].set_ylabel(f"Y={y:.1f}", fontsize=7)

    fig.suptitle(
        f"Scan Overview | rendered={rendered} | measured={len(scan_ctx.results)}/{scan_ctx.total_points} | cell # = goto index",
        fontsize=10,
    )
    fig.tight_layout()

    output_folder = Path(scan_ctx.payload_output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / "scan_overview.png"
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    success(f"Saved scan overview image: {output_path}")
    info("Overview image shows one trace preview per scan grid point.")
    return output_path
