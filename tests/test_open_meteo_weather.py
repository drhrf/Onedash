from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

from onedash.datasources.base import SourceStatus
from onedash.datasources.open_meteo_weather import BASE_URL, OpenMeteoWeatherSource
from tests.conftest import load_fixture


@pytest.fixture
def source():
    return OpenMeteoWeatherSource()


class TestOpenMeteoWeatherHappyPath:
    @responses.activate
    def test_returns_ok_with_one_record(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_weather_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert len(result.records) == 1
        assert result.records[0].value == 22.5

    @responses.activate
    def test_observation_time_is_parsed_as_utc(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_weather_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.observation_time == datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)

    @responses.activate
    def test_request_uses_expected_params(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_weather_happy.json"), status=200)
        source.fetch(sample_aoi)
        request_url = responses.calls[0].request.url
        query = parse_qs(urlparse(request_url).query)
        assert query["latitude"] == [str(sample_aoi.lat)]
        assert query["longitude"] == [str(sample_aoi.lon)]
        assert query["timezone"] == ["UTC"]
        assert "temperature_2m" in query["current"][0]

    @responses.activate
    def test_no_real_network_call_is_ever_made(self, source, sample_aoi):
        # responses.activate blocks any unmocked request; register a
        # deliberately different body so success here proves the mock path,
        # and any accidental real call would raise ConnectionError instead.
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_weather_happy.json"), status=200)
        source.fetch(sample_aoi)
        assert len(responses.calls) == 1


class TestOpenMeteoWeatherErrorHandling:
    @responses.activate
    def test_http_500_is_error_status(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json={"error": "server error"}, status=500)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert "500" in result.error_message

    @responses.activate
    def test_http_429_is_error_status(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json={"error": "rate limited"}, status=429)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert "429" in result.error_message

    @responses.activate
    def test_timeout_is_error_status(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body=requests.exceptions.Timeout("timed out"))
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert "tempo de resposta" in result.error_message

    @responses.activate
    def test_connection_error_is_error_status(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body=requests.exceptions.ConnectionError("no route"))
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert "conexão" in result.error_message

    @responses.activate
    def test_non_json_body_is_error_status(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body="not-json-at-all{{{", status=200, content_type="text/plain")
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert "JSON" in result.error_message

    @responses.activate
    def test_missing_current_key_is_empty_status(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_weather_no_current.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.EMPTY
        assert result.records == []

    @responses.activate
    def test_missing_time_field_is_error_not_keyerror(self, source, sample_aoi):
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_weather_missing_time.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert result.error_message is not None

    @responses.activate
    def test_bad_field_types_is_error_not_crash(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_weather_bad_types.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_unmocked_request_is_handled_gracefully(self, source, sample_aoi):
        # No mock registered for this URL: `responses` itself raises a
        # connection error for any unmocked request under @responses.activate,
        # deterministically exercising the same code path a real network
        # failure would — without the test's outcome depending on whatever
        # network access happens to be available wherever it runs.
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
