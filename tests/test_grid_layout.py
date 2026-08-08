from __future__ import annotations

import pytest

from onedash.grid_layout import GRID_SHAPES, MAX_PANELS, SUPPORTED_PANEL_COUNTS, compute_rows


class TestComputeRows:
    @pytest.mark.parametrize("n", SUPPORTED_PANEL_COUNTS)
    def test_every_supported_count_covers_all_indices_exactly_once(self, n):
        rows = compute_rows(n)
        flat = [i for row in rows for i in row]
        assert sorted(flat) == list(range(n))

    @pytest.mark.parametrize("n", SUPPORTED_PANEL_COUNTS)
    def test_every_supported_count_matches_declared_shape(self, n):
        rows = compute_rows(n)
        expected_rows, expected_cols = GRID_SHAPES[n]
        assert len(rows) == expected_rows
        assert all(len(row) == expected_cols for row in rows)

    def test_indices_are_in_row_major_order(self):
        assert compute_rows(6) == [[0, 1, 2], [3, 4, 5]]
        assert compute_rows(4) == [[0, 1], [2, 3]]
        assert compute_rows(1) == [[0]]

    @pytest.mark.parametrize("n", [0, -1, 5, 7, 100])
    def test_unsupported_count_raises(self, n):
        with pytest.raises(ValueError):
            compute_rows(n)


class TestConstants:
    def test_max_panels_is_six(self):
        assert MAX_PANELS == 6

    def test_supported_panel_counts_matches_grid_shapes(self):
        assert set(SUPPORTED_PANEL_COUNTS) == set(GRID_SHAPES)

    def test_supported_panel_counts_is_sorted(self):
        assert list(SUPPORTED_PANEL_COUNTS) == sorted(SUPPORTED_PANEL_COUNTS)
