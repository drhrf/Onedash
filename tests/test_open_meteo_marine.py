from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests
import responses

from onedash.datasources.base import SourceStatus
from onedash.datasources.open_meteo_marine import BASE_URL, OpenMeteoMarineSource
from tests.conftest import load_fixture


@pytest.fixture
def source():
    return OpenMeteoMarineSource()


class TestOpenMeteoMarine:
    @responses.activate
    def test_happy_path_with_sea_surface_temperature(self, source, sample_aoi):
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_marine_happy_with_sst.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert result.records[0].value == 1.2
        assert "TSM" in result.records[0].label

    @responses.activate
    def test_happy_path_without_sea_surface_temperature_still_succeeds(self, source, sample_aoi):
        # sea_surface_temperature availability couldn't be verified live;
        # the source must degrade gracefully, not fail, if it's absent.
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_marine_happy_no_sst.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert result.records[0].value == 1.2
        assert "TSM" not in result.records[0].label

    @responses.activate
    def test_observation_time_parsed_as_utc(self, source, sample_aoi):
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_marine_happy_with_sst.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.observation_time == datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)

    @responses.activate
    def test_missing_current_is_empty(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_marine_no_current.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.EMPTY

    @responses.activate
    def test_http_500_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json={}, status=500)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_connection_error_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body=requests.exceptions.ConnectionError())
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_missing_wave_height_field_is_error_not_crash(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json={"current": {"time": "2026-08-08T12:00"}}, status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
