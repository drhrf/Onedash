from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest
from freezegun import freeze_time
from pydantic import ValidationError

from onedash.datasources.base import AreaOfInterest, FetchResult, GeoRecord, SourceStatus


class TestGeoRecord:
    def test_valid_record_constructs(self):
        record = GeoRecord(id="1", lat=-22.88, lon=-42.02, value=25.3, label="teste")
        assert record.lat == -22.88

    def test_none_lat_lon_is_allowed(self):
        record = GeoRecord(id="1")
        assert record.lat is None
        assert record.lon is None

    def test_lat_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            GeoRecord(id="1", lat=120.0, lon=0.0)

    def test_lat_rejects_nan(self):
        with pytest.raises(ValidationError):
            GeoRecord(id="1", lat=math.nan, lon=0.0)

    def test_lon_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            GeoRecord(id="1", lat=0.0, lon=200.0)

    def test_lon_rejects_nan(self):
        with pytest.raises(ValidationError):
            GeoRecord(id="1", lat=0.0, lon=math.nan)

    def test_observation_time_naive_raises(self):
        with pytest.raises(ValidationError):
            GeoRecord(id="1", observation_time=datetime(2026, 1, 1))

    def test_observation_time_aware_is_accepted(self):
        record = GeoRecord(id="1", observation_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert record.observation_time.tzinfo is not None

    def test_raw_defaults_to_empty_dict_and_is_not_shared_between_instances(self):
        a = GeoRecord(id="1")
        b = GeoRecord(id="2")
        a.raw["x"] = 1
        assert b.raw == {}


class TestFetchResult:
    def test_fetched_at_naive_raises(self):
        with pytest.raises(ValidationError):
            FetchResult(source_id="s", status=SourceStatus.OK, fetched_at=datetime(2026, 1, 1))

    def test_fetched_at_aware_is_accepted(self):
        result = FetchResult(
            source_id="s", status=SourceStatus.OK, fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        assert result.status is SourceStatus.OK

    def test_defaults(self):
        result = FetchResult(
            source_id="s", status=SourceStatus.EMPTY, fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        assert result.records == []
        assert result.error_message is None
        assert result.extra == {}


class TestAreaOfInterest:
    def test_to_bbox_matches_geo_utils(self):
        from onedash import geo_utils

        aoi = AreaOfInterest(lat=-22.8894, lon=-42.0286, radius_km=25.0)
        assert aoi.to_bbox() == geo_utils.bbox_from_radius(-22.8894, -42.0286, 25.0)

    def test_invalid_radius_raises(self):
        with pytest.raises(ValidationError):
            AreaOfInterest(lat=0.0, lon=0.0, radius_km=0.0)

    def test_invalid_lat_raises(self):
        with pytest.raises(ValidationError):
            AreaOfInterest(lat=-95.0, lon=0.0)

    def test_default_radius(self):
        aoi = AreaOfInterest(lat=0.0, lon=0.0)
        assert aoi.radius_km == 25.0


class TestDataSourceTemplateMethod:
    def test_successful_fetch_passes_through_unchanged(self, sample_aoi, fake_data_source_cls):
        expected = FetchResult(
            source_id="fake", status=SourceStatus.OK, fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        source = fake_data_source_cls(result=expected)
        result = source.fetch(sample_aoi)
        assert result is expected

    def test_unexpected_exception_is_caught_as_error_status(self, sample_aoi, fake_data_source_cls):
        source = fake_data_source_cls(raise_error=ZeroDivisionError("boom"))
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert "boom" in result.error_message
        assert result.records == []

    def test_error_path_never_raises_into_caller(self, sample_aoi, fake_data_source_cls):
        source = fake_data_source_cls(raise_error=KeyError("missing"))
        # Should not raise — this is the whole point of the template method.
        source.fetch(sample_aoi)

    @freeze_time("2026-08-08T12:00:00Z")
    def test_default_clock_uses_current_utc_time(self, sample_aoi, fake_data_source_cls):
        source = fake_data_source_cls(raise_error=RuntimeError("x"))
        result = source.fetch(sample_aoi)
        assert result.fetched_at == datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)

    def test_injected_clock_is_used_on_error_path(self, sample_aoi, fake_data_source_cls):
        fixed = datetime(2020, 1, 1, tzinfo=timezone.utc)
        source = fake_data_source_cls(raise_error=RuntimeError("x"), clock=lambda: fixed)
        result = source.fetch(sample_aoi)
        assert result.fetched_at == fixed


class TestDataSourceResultHelpers:
    def test_ok_helper_sets_status_and_records(self, fake_data_source_cls):
        source = fake_data_source_cls()
        record = GeoRecord(id="1", lat=0.0, lon=0.0)
        result = source._ok([record], observation_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert result.status is SourceStatus.OK
        assert result.records == [record]
        assert result.source_id == "fake"

    def test_empty_helper(self, fake_data_source_cls):
        result = fake_data_source_cls()._empty()
        assert result.status is SourceStatus.EMPTY
        assert result.records == []

    def test_error_helper_carries_message(self, fake_data_source_cls):
        result = fake_data_source_cls()._error("deu ruim")
        assert result.status is SourceStatus.ERROR
        assert result.error_message == "deu ruim"

    def test_unsupported_location_helper(self, fake_data_source_cls):
        result = fake_data_source_cls()._unsupported_location("fora do Brasil")
        assert result.status is SourceStatus.UNSUPPORTED_LOCATION
        assert result.error_message == "fora do Brasil"
