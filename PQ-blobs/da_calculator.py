"""
Data Availability Calculator — Two-Tier Node Network
=====================================================

Finds the minimum number of blobs `b` that each full node must download so
that P(any blob unavailable) < max_failure_prob, across a sweep of parameter
combinations.

Network model
-------------
  - Super nodes  : fraction `super_node_fraction` of all nodes; download ALL blobs.
  - Full nodes   : the remaining nodes; each downloads `b` blobs chosen uniformly
                   at random (seeded by H(node_id || block_hash)).

Honesty model
-------------
Every node is independently honest with probability `honest_fraction`.
Only honest nodes serve data to the network.

Probability derivation
----------------------
For a specific blob i, both tiers must simultaneously fail to hold it:

  P(super nodes miss blob i) = (1 - honest_fraction) ^ num_super_nodes
  P(full nodes  miss blob i) = (1 - honest_fraction * b / total_blobs) ^ num_full_nodes

  P(blob i missing) = product of the two above

Union bound over all blobs:

  P(failure) ≤ total_blobs
               * (1 - honest_fraction) ^ num_super_nodes
               * (1 - honest_fraction * b / total_blobs) ^ num_full_nodes

We search for the smallest integer b such that P(failure) < max_failure_prob.
"""

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LogNorm, Normalize


# =============================================================================
# SWEPT PARAMETERS
# =============================================================================

# Fraction of nodes that are honest (e.g. 0.01 = 1% honest, 99% malicious)
honest_fraction_values = [0.01, 0.02, 0.03, 0.04]

# Number of blobs published per block
total_blobs_values = [32, 64, 128, 256]

# Fraction of total nodes that are super nodes (they download ALL blobs)
super_node_fraction_values = [0.02, 0.04, 0.06, 0.08]


# =============================================================================
# FIXED PARAMETERS
# =============================================================================

# Total number of nodes in the network
total_nodes = 10_000

# Size of each blob in kilobytes
blob_size_kb = 128

# Slot duration in seconds (used to convert download size to bandwidth)
slot_duration_seconds = 12

# Maximum tolerated probability that any blob is unavailable
max_failure_prob = 1e-8


# =============================================================================
# Core formulas
# =============================================================================

def compute_failure_prob(
    total_blobs:         int,
    num_super_nodes:     int,
    num_full_nodes:      int,
    honest_fraction:     float,
    blobs_per_full_node: int,
) -> float:
    """Upper bound on P(any blob is unavailable) via the union bound."""
    prob_super_nodes_miss = (1 - honest_fraction) ** num_super_nodes
    prob_full_nodes_miss  = (
        1 - honest_fraction * blobs_per_full_node / total_blobs
    ) ** num_full_nodes
    return total_blobs * prob_super_nodes_miss * prob_full_nodes_miss


def find_minimum_blobs_per_full_node(
    total_blobs:      int,
    num_super_nodes:  int,
    num_full_nodes:   int,
    honest_fraction:  float,
    max_failure_prob: float,
) -> tuple[int | None, float]:
    """
    Find smallest b in [0, total_blobs] such that P(failure) < max_failure_prob.
    Returns (b, achieved_prob), or (None, prob_at_max_b) if no solution exists.
    """
    for b in range(0, total_blobs + 1):
        prob = compute_failure_prob(
            total_blobs, num_super_nodes, num_full_nodes, honest_fraction, b
        )
        if prob < max_failure_prob:
            return b, prob
    return None, compute_failure_prob(
        total_blobs, num_super_nodes, num_full_nodes, honest_fraction, total_blobs
    )


# =============================================================================
# Compute all results
# =============================================================================

def compute_all_results() -> dict:
    """
    Compute (b, prob) for every (super_node_fraction, honest_fraction, total_blobs)
    combination. Returns a dict keyed by that 3-tuple.
    """
    results = {}
    for s in super_node_fraction_values:
        num_super = round(s * total_nodes)
        num_full  = total_nodes - num_super
        for h in honest_fraction_values:
            for tb in total_blobs_values:
                b, prob = find_minimum_blobs_per_full_node(
                    tb, num_super, num_full, h, max_failure_prob
                )
                results[(s, h, tb)] = (b, prob)
    return results


# =============================================================================
# Text table output (unchanged from previous version)
# =============================================================================

_INDENT  = "  "
_COL_SEP = "  │  "


def _hline(label_width: int, col_width: int, num_cols: int) -> str:
    return (
        _INDENT
        + "─" * label_width
        + "──┼──"
        + "──┼──".join("─" * col_width for _ in range(num_cols))
    )


def print_grid(title, note, col_headers, main_rows, extra_rows=None):
    all_labels = [lbl for lbl, _ in (main_rows + (extra_rows or []))]
    all_cells  = [c for _, cells in (main_rows + (extra_rows or [])) for c in cells]
    label_width = max(len(l) for l in all_labels + [" "])
    col_width   = max(
        max((len(c) for c in all_cells), default=0),
        max(len(h) for h in col_headers),
    )
    hline  = _hline(label_width, col_width, len(col_headers))
    header = (
        _INDENT + " " * label_width + _COL_SEP
        + _COL_SEP.join(f"{h:^{col_width}}" for h in col_headers)
    )
    print(f"  {title}   {note}")
    print(hline)
    print(header)
    print(hline)
    for label, cells in main_rows:
        row = _COL_SEP.join(f"{c:^{col_width}}" for c in cells)
        print(f"{_INDENT}{label:{label_width}}{_COL_SEP}{row}")
    if extra_rows:
        print(hline)
        for label, cells in extra_rows:
            row = _COL_SEP.join(f"{c:^{col_width}}" for c in cells)
            print(f"{_INDENT}{label:{label_width}}{_COL_SEP}{row}")
    print(hline)
    print()


def _fmt_b(b):          return "N/A" if b is None else str(b)
def _fmt_download(b):   return "N/A" if b is None else (f"{b*blob_size_kb/1024:.2f}MB" if b*blob_size_kb >= 1024 else f"{b*blob_size_kb}KB")
def _fmt_bandwidth(b):  return "N/A" if b is None else f"{b*blob_size_kb/slot_duration_seconds:.1f}KB/s"
def _fmt_prob(prob):    return f"{prob:.2e}{'  !' if prob >= max_failure_prob else ''}"


def print_text_tables(all_results: dict) -> None:
    col_headers = [f"{tb} blobs" for tb in total_blobs_values]

    for s in super_node_fraction_values:
        num_super = round(s * total_nodes)
        num_full  = total_nodes - num_super

        def lbl(h):
            return f"h={h:.0%}  ({h*num_super:.0f} hon.super / {h*num_full:.0f} hon.full)"

        rows_b  = [(lbl(h), [_fmt_b(all_results[(s,h,tb)][0])        for tb in total_blobs_values]) for h in honest_fraction_values]
        rows_dl = [(lbl(h), [_fmt_download(all_results[(s,h,tb)][0])  for tb in total_blobs_values]) for h in honest_fraction_values]
        rows_bw = [(lbl(h), [_fmt_bandwidth(all_results[(s,h,tb)][0]) for tb in total_blobs_values]) for h in honest_fraction_values]
        rows_pr = [(lbl(h), [_fmt_prob(all_results[(s,h,tb)][1])      for tb in total_blobs_values]) for h in honest_fraction_values]

        super_dl = [("super nodes (all h)", [_fmt_download(tb)  for tb in total_blobs_values])]
        super_bw = [("super nodes (all h)", [_fmt_bandwidth(tb) for tb in total_blobs_values])]

        print(f"{'─'*70}")
        print(f"  Super node fraction: {s:.0%}  ({num_super:,} super / {num_full:,} full nodes)")
        print(f"{'─'*70}\n")
        print_grid("Minimum blobs per full node  (b)", "", col_headers, rows_b)
        print_grid("Data downloaded per slot", f"[blob={blob_size_kb}KB]", col_headers, rows_dl, super_dl)
        print_grid("Bandwidth required", f"[slot={slot_duration_seconds}s]", col_headers, rows_bw, super_bw)
        print_grid("Achieved P(failure)", f"[target<{max_failure_prob:.0e}]  (!=above target)", col_headers, rows_pr)


# =============================================================================
# Heatmap figures
# =============================================================================

def _cell_brightness(rgba: tuple) -> float:
    """Perceived brightness of an RGBA colour (0=dark, 1=bright)."""
    return 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]


def _build_matrix(all_results: dict, super_node_fraction: float, value_fn) -> np.ndarray:
    """Build a 2-D array: rows = honest_fraction, cols = total_blobs."""
    rows, cols = len(honest_fraction_values), len(total_blobs_values)
    mat = np.empty((rows, cols))
    for i, h in enumerate(honest_fraction_values):
        for j, tb in enumerate(total_blobs_values):
            b, prob = all_results[(super_node_fraction, h, tb)]
            mat[i, j] = value_fn(b, prob, tb)
    return mat


def generate_heatmaps(all_results: dict) -> None:
    """
    Produce four heatmap figures (one per metric), each with one subplot per
    super_node_fraction value. Figures are saved as PNG files.
    """

    # ── Metric definitions ───────────────────────────────────────────────────
    # Each entry: (file_suffix, figure_title, value_fn, annotation_fn, use_log_scale)
    #
    # value_fn(b, prob, tb) → float used for colour mapping
    # annotation_fn(v)      → str displayed inside the cell
    # ─────────────────────────────────────────────────────────────────────────

    _LARGE = 1e-300   # floor for log scale (avoids log(0))

    metrics = [
        (
            "min_b",
            "Minimum blobs per full node  (b)",
            lambda b, prob, tb: float(b) if b is not None else float(tb),
            lambda v: str(int(v)),
            False,
        ),
        (
            "download_per_slot",
            f"Data downloaded per slot  [blob = {blob_size_kb} KB]",
            lambda b, prob, tb: float(b * blob_size_kb) if b is not None else 0.0,
            lambda v: f"{v/1024:.2f} MB" if v >= 1024 else f"{int(v)} KB",
            False,
        ),
        (
            "bandwidth",
            f"Bandwidth required  [slot = {slot_duration_seconds} s]",
            lambda b, prob, tb: float(b * blob_size_kb / slot_duration_seconds) if b is not None else 0.0,
            lambda v: f"{v:.1f} KB/s",
            False,
        ),
        (
            "p_failure",
            f"Achieved P(failure)  [target < {max_failure_prob:.0e}]",
            lambda b, prob, tb: max(prob, _LARGE),
            lambda v: f"{v:.1e}" if v > _LARGE * 100 else "≈ 0",
            True,   # log scale
        ),
    ]

    n_super = len(super_node_fraction_values)
    x_labels = [str(tb) for tb in total_blobs_values]
    y_labels  = [f"{h:.0%}" for h in honest_fraction_values]

    saved_files = []

    for file_suffix, fig_title, value_fn, ann_fn, use_log in metrics:

        fig, axes_grid = plt.subplots(2, 2, figsize=(13, 10))
        axes = axes_grid.ravel()   # flat list: top-left, top-right, bottom-left, bottom-right

        # Build all matrices first to get a consistent colour scale
        matrices = {
            s: _build_matrix(all_results, s, value_fn)
            for s in super_node_fraction_values
        }

        all_vals = np.concatenate([m.ravel() for m in matrices.values()])
        vmin = float(np.min(all_vals[all_vals > 0])) if use_log else float(np.min(all_vals))
        vmax = float(np.max(all_vals))

        # Guard: identical min/max
        if vmin == vmax:
            vmax = vmin + 1

        norm = LogNorm(vmin=vmin, vmax=vmax) if use_log else Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.cm.RdYlGn_r

        for ax, s in zip(axes, super_node_fraction_values):
            num_super = round(s * total_nodes)
            mat = matrices[s]

            im = ax.imshow(mat, cmap=cmap, norm=norm, aspect="auto")

            # Cell annotations
            for i in range(len(honest_fraction_values)):
                for j in range(len(total_blobs_values)):
                    v    = mat[i, j]
                    text = ann_fn(v)

                    # Mark P(failure) cells that exceed the target
                    if file_suffix == "p_failure" and v >= max_failure_prob:
                        text += " !"

                    rgba       = cmap(norm(v))
                    text_color = "black" if _cell_brightness(rgba) > 0.45 else "white"

                    ax.text(
                        j, i, text,
                        ha="center", va="center",
                        fontsize=8, color=text_color, fontweight="bold",
                        path_effects=[
                            pe.withStroke(linewidth=1.5,
                                          foreground="white" if text_color == "black" else "black")
                        ],
                    )

            ax.set_xticks(range(len(total_blobs_values)))
            ax.set_xticklabels(x_labels, fontsize=9)
            ax.set_yticks(range(len(honest_fraction_values)))
            ax.set_yticklabels(y_labels, fontsize=9)
            ax.set_xlabel("total blobs per block", fontsize=9)
            ax.set_ylabel("honest fraction  (h)", fontsize=9)
            ax.set_title(
                f"super nodes = {s:.0%}  ({num_super:,} nodes)",
                fontsize=10, fontweight="bold", pad=8,
            )

        # Main title (metric name)
        fig.suptitle(fig_title, fontsize=14, fontweight="bold", y=0.98)

        # Fixed-params subtitle, sitting just below the suptitle
        fig.text(
            0.5, 0.935,
            f"N={total_nodes:,}  blob={blob_size_kb} KB  slot={slot_duration_seconds} s  "
            f"target P(fail) < {max_failure_prob:.0e}",
            ha="center", va="top", fontsize=9, color="#555555",
        )

        # Reserve space: top for titles, right for dedicated colorbar axis
        fig.subplots_adjust(top=0.88, bottom=0.08, left=0.08, right=0.84, hspace=0.38, wspace=0.32)

        # Dedicated colorbar axis — positioned in the right margin, not overlapping subplots
        cbar_ax = fig.add_axes([0.86, 0.12, 0.025, 0.72])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, cax=cbar_ax)
        cbar.set_label(fig_title, fontsize=9, labelpad=10)

        fname = f"da_heatmap_{file_suffix}.png"
        plt.savefig(fname, dpi=150, bbox_inches="tight")
        plt.close()
        saved_files.append(fname)
        print(f"  Saved: {fname}")

    return saved_files


# =============================================================================
# Entry point
# =============================================================================

def run() -> None:
    print(f"\n{'═'*70}")
    print(f"  Data Availability Calculator — Two-Tier Node Network")
    print(f"{'═'*70}")
    print(f"  Fixed:   N={total_nodes:,}   blob={blob_size_kb}KB   "
          f"slot={slot_duration_seconds}s   target P(fail)<{max_failure_prob:.0e}")
    print(f"  Swept:   h ∈ {[f'{h:.0%}' for h in honest_fraction_values]}")
    print(f"           blobs ∈ {total_blobs_values}")
    print(f"           super_node_fraction ∈ {[f'{s:.0%}' for s in super_node_fraction_values]}")
    print(f"{'═'*70}\n")

    all_results = compute_all_results()

    print_text_tables(all_results)

    print(f"\n{'═'*70}")
    print("  Generating heatmap figures ...")
    print(f"{'═'*70}")
    generate_heatmaps(all_results)
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    run()
