from __future__ import annotations

from datetime import datetime, timezone

import pytest

from onedash.datasources.base import AreaOfInterest, FetchResult, SourceStatus
from onedash.datasources.cached import fetch_layer
from onedash.datasources.open_meteo_weather import OpenMeteoWeatherSource

FETCHED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clear_cache():
    # st.cache_data's cache is process-global and persists across test
    # functions by default; without clearing, an earlier test's cached
    # result could leak into a later test that expects a fresh call.
    fetch_layer.clear()
    yield
    fetch_layer.clear()


@pytest.fixture
def call_counter(monkeypatch):
    calls = []

    def fake_fetch(self, aoi, params=None):
        calls.append((aoi.lat, aoi.lon, aoi.radius_km, dict(params or {})))
        return FetchResult(
            source_id=self.source_id, status=SourceStatus.OK, fetched_at=FETCHED_AT
        )

    monkeypatch.setattr(OpenMeteoWeatherSource, "fetch", fake_fetch)
    return calls


class TestFetchLayerCaching:
    def test_calls_underlying_source_and_returns_its_result(self, call_counter):
        result = fetch_layer("open_meteo_weather", -22.8894, -42.0286, 25.0)
        assert result.status is SourceStatus.OK
        assert len(call_counter) == 1

    def test_identical_arguments_hit_cache_not_source(self, call_counter):
        fetch_layer("open_meteo_weather", -22.8894, -42.0286, 25.0)
        fetch_layer("open_meteo_weather", -22.8894, -42.0286, 25.0)
        assert len(call_counter) == 1

    def test_different_coordinates_are_not_cached_together(self, call_counter):
        fetch_layer("open_meteo_weather", -22.8894, -42.0286, 25.0)
        fetch_layer("open_meteo_weather", -23.0, -42.0286, 25.0)
        assert len(call_counter) == 2

    def test_different_radius_is_not_cached_together(self, call_counter):
        fetch_layer("open_meteo_weather", -22.8894, -42.0286, 25.0)
        fetch_layer("open_meteo_weather", -22.8894, -42.0286, 50.0)
        assert len(call_counter) == 2

    def test_disease_param_only_passed_for_infodengue(self, monkeypatch):
        from onedash.datasources.infodengue import InfoDengueSource

        seen_params = []

        def fake_fetch(self, aoi, params=None):
            seen_params.append(dict(params or {}))
            return FetchResult(source_id=self.source_id, status=SourceStatus.OK, fetched_at=FETCHED_AT)

        monkeypatch.setattr(OpenMeteoWeatherSource, "fetch", fake_fetch)
        monkeypatch.setattr(InfoDengueSource, "fetch", fake_fetch)

        fetch_layer("open_meteo_weather", -22.8894, -42.0286, 25.0)
        fetch_layer("infodengue", -22.8894, -42.0286, 25.0, disease="zika")

        assert seen_params[0] == {}
        assert seen_params[1] == {"disease": "zika"}
