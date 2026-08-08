from __future__ import annotations

GRID_SHAPES: dict[int, tuple[int, int]] = {1: (1, 1), 2: (1, 2), 3: (1, 3), 4: (2, 2), 6: (2, 3)}

SUPPORTED_PANEL_COUNTS: tuple[int, ...] = tuple(sorted(GRID_SHAPES))
MAX_PANELS: int = max(SUPPORTED_PANEL_COUNTS)


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
