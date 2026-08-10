from __future__ import annotations

GRID_SHAPES: dict[int, tuple[int, int]] = {1: (1, 1), 2: (1, 2), 3: (1, 3), 4: (2, 2), 6: (2, 3)}

SUPPORTED_PANEL_COUNTS: tuple[int, ...] = tuple(sorted(GRID_SHAPES))
MAX_PANELS: int = max(SUPPORTED_PANEL_COUNTS)


MAP_HEIGHTS_PX: dict[int, int] = {1: 520, 2: 460, 3: 380, 4: 380, 6: 300}


def map_height_px(n: int) -> int:
    """Per-map pixel height for a grid of n panels. Small multiples only work
    if you can actually see them side by side — a fixed height that suits a
    single map turns a 6-panel grid into several screens of scrolling, which
    defeats the point of comparing layers at a glance."""
    if n not in MAP_HEIGHTS_PX:
        raise ValueError(f"unsupported panel count: {n}")
    return MAP_HEIGHTS_PX[n]


def compute_rows(n: int) -> list[list[int]]:
    """Returns panel indices grouped into rows for a given panel count.
    Indices are always the contiguous range 0..n-1 in row-major order, so a
    given logical panel (e.g. index 0) keeps the same index — and therefore
    the same widget keys/session state — regardless of how many panels are
    currently visible."""
    if n not in GRID_SHAPES:
        raise ValueError(f"unsupported panel count: {n}")
    rows, cols = GRID_SHAPES[n]
    it = iter(range(n))
    return [[next(it) for _ in range(cols)] for _ in range(rows)]
