from __future__ import annotations

import pytest

from onedash.grid_layout import (
    GRID_SHAPES,
    MAP_HEIGHTS_PX,
    MAX_PANELS,
    SUPPORTED_PANEL_COUNTS,
    compute_rows,
    map_height_px,
)


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


class TestMapHeight:
    @pytest.mark.parametrize("n", SUPPORTED_PANEL_COUNTS)
    def test_every_supported_count_has_a_positive_height(self, n):
        assert map_height_px(n) > 0

    def test_height_never_grows_as_panels_are_added(self):
        heights = [map_height_px(n) for n in SUPPORTED_PANEL_COUNTS]
        assert heights == sorted(heights, reverse=True)

    def test_six_panels_are_shorter_than_one(self):
        # The point of small multiples is seeing them at once; a 6-panel grid
        # at single-map height would be several screens of scrolling.
        assert map_height_px(6) < map_height_px(1)

    @pytest.mark.parametrize("n", [0, -1, 5, 7, 100])
    def test_unsupported_count_raises(self, n):
        with pytest.raises(ValueError):
            map_height_px(n)

    def test_heights_cover_exactly_the_supported_counts(self):
        assert set(MAP_HEIGHTS_PX) == set(GRID_SHAPES)


class TestConstants:
    def test_max_panels_is_six(self):
        assert MAX_PANELS == 6

    def test_supported_panel_counts_matches_grid_shapes(self):
        assert set(SUPPORTED_PANEL_COUNTS) == set(GRID_SHAPES)

    def test_supported_panel_counts_is_sorted(self):
        assert list(SUPPORTED_PANEL_COUNTS) == sorted(SUPPORTED_PANEL_COUNTS)
