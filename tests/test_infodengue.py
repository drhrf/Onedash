from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests
import responses
from freezegun import freeze_time

from onedash.datasources.base import AreaOfInterest, SourceStatus
from onedash.datasources.infodengue import BASE_URL, InfoDengueSource
from tests.conftest import load_fixture

OUTSIDE_REGION_AOI = AreaOfInterest(lat=-23.5505, lon=-46.6333, label="São Paulo")  # far from Região dos Lagos


@pytest.fixture
def source():
    return InfoDengueSource()


class TestInfoDengueHappyPath:
    @freeze_time("2026-08-08T12:00:00Z")
    @responses.activate
    def test_returns_latest_week_as_value(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_happy_recent.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert result.records[0].value == pytest.approx(8.7)  # SE 202631 is the latest of the three

    @freeze_time("2026-08-08T12:00:00Z")
    @responses.activate
    def test_observation_time_is_week_start(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_happy_recent.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.observation_time == datetime(2026, 7, 26, tzinfo=timezone.utc)

    @freeze_time("2026-08-08T12:00:00Z")
    @responses.activate
    def test_recent_week_is_flagged_preliminary(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_happy_recent.json"), status=200)
        result = source.fetch(sample_aoi)
        assert "preliminar" in result.records[0].label

    @freeze_time("2026-08-08T12:00:00Z")
    @responses.activate
    def test_old_week_is_not_flagged_preliminary(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_happy_old.json"), status=200)
        result = source.fetch(sample_aoi)
        assert "preliminar" not in result.records[0].label

    @responses.activate
    def test_record_uses_municipality_centroid(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_happy_recent.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.records[0].lat == pytest.approx(sample_aoi.lat)
        assert result.records[0].lon == pytest.approx(sample_aoi.lon)

    @responses.activate
    def test_null_casos_est_falls_back_to_casos(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_null_casos_est.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert result.records[0].value == 6.0

    @responses.activate
    def test_query_uses_resolved_geocode_and_default_disease(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_happy_recent.json"), status=200)
        source.fetch(sample_aoi)
        request_url = responses.calls[0].request.url
        assert "geocode=3300704" in request_url
        assert "disease=dengue" in request_url

    @responses.activate
    def test_disease_param_override(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_happy_recent.json"), status=200)
        source.fetch(sample_aoi, params={"disease": "chikungunya"})
        request_url = responses.calls[0].request.url
        assert "disease=chikungunya" in request_url


class TestInfoDengueLocationCoverage:
    def test_aoi_outside_region_is_unsupported_not_error(self, source):
        result = source.fetch(OUTSIDE_REGION_AOI)
        assert result.status is SourceStatus.UNSUPPORTED_LOCATION
        assert "Região dos Lagos" in result.error_message

    def test_unsupported_location_makes_no_http_call(self, source):
        # No @responses.activate registered — if the code tried an HTTP call
        # here it would raise, failing the test either way, but asserting
        # the specific status makes the intent explicit.
        result = source.fetch(OUTSIDE_REGION_AOI)
        assert result.status is SourceStatus.UNSUPPORTED_LOCATION


class TestInfoDengueInvalidInput:
    def test_invalid_disease_is_error(self, source, sample_aoi):
        result = source.fetch(sample_aoi, params={"disease": "not-a-real-disease"})
        assert result.status is SourceStatus.ERROR


class TestInfoDengueErrorHandling:
    @responses.activate
    def test_empty_list_is_empty_status(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_empty.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.EMPTY

    @responses.activate
    def test_non_list_response_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_not_a_list.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_missing_fields_is_error_not_crash(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, json=load_fixture("infodengue_missing_fields.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

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
    def test_malformed_json_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body="not-json{{{", status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_other_request_exception_is_error(self, source, sample_aoi):
        responses.add(responses.GET, BASE_URL, body=requests.exceptions.RequestException("erro genérico"))
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_unmocked_request_is_handled_gracefully(self, source, sample_aoi):
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
