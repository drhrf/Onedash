from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from onedash import geo_utils


class TestInRangeOrNone:
    def test_none_is_always_valid(self):
        assert geo_utils.in_range_or_none(None, -90.0, 90.0) is True

    def test_value_within_range(self):
        assert geo_utils.in_range_or_none(0.0, -90.0, 90.0) is True

    def test_value_at_boundary_is_valid(self):
        assert geo_utils.in_range_or_none(90.0, -90.0, 90.0) is True
        assert geo_utils.in_range_or_none(-90.0, -90.0, 90.0) is True

    def test_value_above_range(self):
        assert geo_utils.in_range_or_none(90.1, -90.0, 90.0) is False

    def test_value_below_range(self):
        assert geo_utils.in_range_or_none(-90.1, -90.0, 90.0) is False

    def test_nan_is_rejected(self):
        # Regression guard: `v < low or v > high` fails OPEN for NaN (both
        # comparisons are False), silently accepting invalid coordinates.
        # The chained comparison used in in_range_or_none fails CLOSED.
        assert geo_utils.in_range_or_none(math.nan, -90.0, 90.0) is False

    def test_positive_infinity_is_rejected(self):
        assert geo_utils.in_range_or_none(math.inf, -90.0, 90.0) is False

    def test_negative_infinity_is_rejected(self):
        assert geo_utils.in_range_or_none(-math.inf, -90.0, 90.0) is False


class TestParseIso8601Utc:
    def test_z_suffix_is_parsed_as_utc(self):
        result = geo_utils.parse_iso8601_utc("2024-06-01T12:00:00Z")
        assert result == datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_explicit_offset_is_converted_to_utc(self):
        result = geo_utils.parse_iso8601_utc("2024-06-01T09:00:00-03:00")
        assert result == datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_naive_string_without_flag_raises(self):
        with pytest.raises(ValueError):
            geo_utils.parse_iso8601_utc("2024-06-01T12:00:00")

    def test_naive_string_with_flag_assumes_utc(self):
        result = geo_utils.parse_iso8601_utc("2024-06-01T12:00:00", assume_utc_if_naive=True)
        assert result == datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_malformed_string_raises(self):
        with pytest.raises(ValueError):
            geo_utils.parse_iso8601_utc("not-a-timestamp")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            geo_utils.parse_iso8601_utc("")


class TestBboxFromRadius:
    def test_basic_bbox_surrounds_center(self):
        south, west, north, east = geo_utils.bbox_from_radius(-22.8894, -42.0286, 25.0)
        assert south < -22.8894 < north
        assert west < -42.0286 < east

    def test_larger_radius_gives_larger_bbox(self):
        small = geo_utils.bbox_from_radius(-22.8894, -42.0286, 10.0)
        large = geo_utils.bbox_from_radius(-22.8894, -42.0286, 50.0)
        small_south, small_west, small_north, small_east = small
        large_south, large_west, large_north, large_east = large
        assert (large_north - large_south) > (small_north - small_south)
        assert (large_east - large_west) > (small_east - small_west)

    def test_zero_radius_raises(self):
        with pytest.raises(ValueError):
            geo_utils.bbox_from_radius(-22.8894, -42.0286, 0.0)

    def test_negative_radius_raises(self):
        with pytest.raises(ValueError):
            geo_utils.bbox_from_radius(-22.8894, -42.0286, -10.0)

    def test_invalid_lat_raises(self):
        with pytest.raises(ValueError):
            geo_utils.bbox_from_radius(120.0, -42.0286, 25.0)

    def test_clamps_north_at_north_pole(self):
        south, west, north, east = geo_utils.bbox_from_radius(89.9, 0.0, 500.0)
        assert north == 90.0

    def test_clamps_south_at_south_pole(self):
        south, west, north, east = geo_utils.bbox_from_radius(-89.9, 0.0, 500.0)
        assert south == -90.0

    def test_near_pole_does_not_raise_zero_division(self):
        # cos(lat) approaches 0 near the poles; must not divide by zero.
        geo_utils.bbox_from_radius(89.999, 0.0, 10.0)


class TestHaversineKm:
    def test_same_point_is_zero_distance(self):
        assert geo_utils.haversine_km(-22.8894, -42.0286, -22.8894, -42.0286) == pytest.approx(0.0, abs=1e-9)

    def test_one_degree_longitude_at_equator_is_about_111_km(self):
        # Definitional check: 1 degree of longitude at the equator is the
        # same ~111.32 km/degree constant used by bbox_from_radius.
        distance = geo_utils.haversine_km(0.0, 0.0, 0.0, 1.0)
        assert distance == pytest.approx(geo_utils.KM_PER_DEGREE_LAT, abs=0.2)

    def test_one_degree_latitude_is_about_111_km(self):
        distance = geo_utils.haversine_km(0.0, 0.0, 1.0, 0.0)
        assert distance == pytest.approx(111.19, abs=0.2)

    def test_is_symmetric(self):
        a = geo_utils.haversine_km(-22.8894, -42.0286, -22.7469, -41.8817)
        b = geo_utils.haversine_km(-22.7469, -41.8817, -22.8894, -42.0286)
        assert a == pytest.approx(b)

    def test_neighboring_regiao_dos_lagos_towns_are_a_plausible_distance_apart(self):
        # Cabo Frio to Armação dos Búzios: neighboring coastal towns, clearly
        # not the same spot but well within the same small region.
        distance = geo_utils.haversine_km(-22.8894, -42.0286, -22.7469, -41.8817)
        assert 10.0 < distance < 40.0
