from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests
import responses

from onedash.datasources.base import SourceStatus
from onedash.datasources.open_meteo_air_quality import BASE_URL, OpenMeteoAirQualitySource
from tests.conftest import load_fixture


@pytest.fixture
def source():
    return OpenMeteoAirQualitySource()


class TestOpenMeteoAirQuality:
    @responses.activate
    def test_happy_path_returns_ok(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_air_quality_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert result.records[0].value == 34

    @responses.activate
    def test_observation_time_parsed_as_utc(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_air_quality_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.observation_time == datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)

    @responses.activate
    def test_missing_current_is_empty(self, source, sample_aoi):
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_air_quality_no_current.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.EMPTY

    @responses.activate
    def test_http_500_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json={}, status=500)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_timeout_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body=requests.exceptions.Timeout())
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_other_request_exception_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body=requests.exceptions.RequestException("erro genérico"))
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_missing_us_aqi_field_is_error_not_crash(self, source, sample_aoi):
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_air_quality_missing_us_aqi.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_malformed_json_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body="{{{not json", status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_unmocked_request_is_handled_gracefully(self, source, sample_aoi):
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
