from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from onedash.freshness import (
    THRESHOLDS,
    FreshnessLevel,
    aggregate_observation_time,
    compute_freshness,
)

NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)


class TestComputeFreshness:
    def test_within_good_threshold_is_fresh(self):
        obs = NOW - timedelta(minutes=30)
        result = compute_freshness(obs, profile="weather", now=NOW)
        assert result.level is FreshnessLevel.FRESH

    def test_between_thresholds_is_aging(self):
        obs = NOW - timedelta(hours=6)
        result = compute_freshness(obs, profile="weather", now=NOW)
        assert result.level is FreshnessLevel.AGING

    def test_beyond_warn_threshold_is_stale(self):
        obs = NOW - timedelta(hours=13)
        result = compute_freshness(obs, profile="weather", now=NOW)
        assert result.level is FreshnessLevel.STALE

    def test_boundary_exactly_at_good_max_is_fresh(self):
        good_max = THRESHOLDS["weather"].good_max
        result = compute_freshness(NOW - good_max, profile="weather", now=NOW)
        assert result.level is FreshnessLevel.FRESH

    def test_boundary_exactly_at_warn_max_is_aging(self):
        warn_max = THRESHOLDS["weather"].warn_max
        result = compute_freshness(NOW - warn_max, profile="weather", now=NOW)
        assert result.level is FreshnessLevel.AGING

    def test_none_observation_time_is_unknown(self):
        result = compute_freshness(None, profile="weather", now=NOW)
        assert result.level is FreshnessLevel.UNKNOWN
        assert result.lag is None

    def test_naive_observation_time_raises(self):
        naive = datetime(2026, 8, 8, 11, 0, 0)
        with pytest.raises(ValueError):
            compute_freshness(naive, profile="weather", now=NOW)

    def test_naive_now_raises(self):
        obs = NOW - timedelta(minutes=30)
        with pytest.raises(ValueError):
            compute_freshness(obs, profile="weather", now=datetime(2026, 8, 8, 12, 0, 0))

    def test_future_timestamp_is_unknown_not_negative(self):
        future = NOW + timedelta(hours=1)
        result = compute_freshness(future, profile="weather", now=NOW)
        assert result.level is FreshnessLevel.UNKNOWN
        assert "futuro" in result.description

    def test_unknown_profile_falls_back_to_default(self):
        obs = NOW - THRESHOLDS["default"].good_max
        result = compute_freshness(obs, profile="does-not-exist", now=NOW)
        assert result.level is FreshnessLevel.FRESH

    def test_non_utc_aware_timestamps_are_normalized(self):
        # 09:00 in UTC-03:00 == 12:00 UTC == exactly "now"
        obs = datetime(2026, 8, 8, 9, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
        result = compute_freshness(obs, profile="weather", now=NOW)
        assert result.lag == timedelta(0)
        assert result.level is FreshnessLevel.FRESH

    def test_epidemiological_profile_tolerates_two_week_lag(self):
        obs = NOW - timedelta(weeks=2)
        result = compute_freshness(obs, profile="epidemiological", now=NOW)
        assert result.level is FreshnessLevel.FRESH

    def test_defaults_to_current_time_when_now_omitted(self):
        obs = datetime.now(timezone.utc) - timedelta(minutes=1)
        result = compute_freshness(obs, profile="weather")
        assert result.level is FreshnessLevel.FRESH


class TestAggregateObservationTime:
    def test_empty_list_returns_none(self):
        assert aggregate_observation_time([]) is None

    def test_all_none_returns_none(self):
        assert aggregate_observation_time([None, None]) is None

    def test_odd_count_returns_exact_median(self):
        t1 = NOW - timedelta(days=3)
        t2 = NOW - timedelta(days=2)
        t3 = NOW - timedelta(days=1)
        assert aggregate_observation_time([t3, t1, t2]) == t2

    def test_even_count_returns_midpoint(self):
        t1 = NOW - timedelta(days=2)
        t2 = NOW - timedelta(days=0)
        result = aggregate_observation_time([t1, t2])
        assert result == NOW - timedelta(days=1)

    def test_none_values_are_filtered_out(self):
        t1 = NOW - timedelta(days=1)
        assert aggregate_observation_time([None, t1, None]) == t1

    def test_mixed_timezones_are_normalized_before_comparison(self):
        t1 = NOW - timedelta(days=1)
        t2_non_utc = (NOW - timedelta(days=2)).astimezone(timezone(timedelta(hours=-3)))
        result = aggregate_observation_time([t1, t2_non_utc])
        assert result.tzinfo == timezone.utc
