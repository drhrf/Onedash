from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs

import pytest
import requests
import responses

from onedash.datasources.base import AreaOfInterest, SourceStatus
from onedash.datasources.overpass_health import BASE_URL, OverpassHealthSource
from tests.conftest import load_fixture


@pytest.fixture
def sleeps():
    """Records requested backoff delays instead of actually sleeping."""
    return []


@pytest.fixture
def source(sleeps):
    return OverpassHealthSource(sleep=lambda seconds: sleeps.append(seconds))


class TestOverpassHealthHappyPath:
    @responses.activate
    def test_returns_all_records(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert len(result.records) == 3

    @responses.activate
    def test_named_facility_uses_its_name(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        labels = {r.label for r in result.records}
        assert "Hospital Municipal Álvaro Alvim" in labels

    @responses.activate
    def test_unnamed_facility_falls_back_to_amenity_label(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        labels = {r.label for r in result.records}
        assert "Farmácia" in labels  # element 100002 has amenity=pharmacy but no name tag

    @responses.activate
    def test_observation_time_is_median_of_records(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        # timestamps: 2024-03-15, 2022-11-02, 2025-01-20 -> median is 2024-03-15
        assert result.observation_time == datetime(2024, 3, 15, 10, 22, 0, tzinfo=timezone.utc)

    @responses.activate
    def test_query_uses_bbox_from_aoi(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_happy.json"), status=200)
        source.fetch(sample_aoi)
        raw_body = responses.calls[0].request.body
        query = parse_qs(raw_body)["data"][0]
        assert 'node["amenity"="hospital"]' in query
        assert "out meta;" in query


class TestOverpassHealthEdgeCases:
    @responses.activate
    def test_empty_bbox_is_empty_not_error(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_empty.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.EMPTY

    def test_oversized_radius_rejected_before_any_request(self, source):
        big_aoi = AreaOfInterest(lat=-22.88, lon=-42.02, radius_km=500.0)
        result = source.fetch(big_aoi)
        assert result.status is SourceStatus.ERROR
        assert "raio" in result.error_message

    @responses.activate
    def test_missing_elements_key_is_error_not_crash(self, source, sample_aoi):
        responses.add(
            responses.POST, BASE_URL, json=load_fixture("overpass_health_missing_elements_key.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_malformed_json_is_error_not_crash(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, body="{{{truncated", status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR

    @responses.activate
    def test_missing_timestamps_yields_unknown_freshness_not_crash(self, source, sample_aoi):
        responses.add(
            responses.POST, BASE_URL, json=load_fixture("overpass_health_missing_timestamps.json"), status=200
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert result.observation_time is None
        assert all(r.observation_time is None for r in result.records)

    @responses.activate
    def test_element_without_coords_is_skipped_others_kept(self, source, sample_aoi):
        responses.add(
            responses.POST,
            BASE_URL,
            json=load_fixture("overpass_health_one_element_without_coords.json"),
            status=200,
        )
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert len(result.records) == 1
        assert result.records[0].label == "Hospital Válido"


class TestOverpassHealthRetryBehavior:
    @responses.activate
    def test_429_is_retried_and_then_succeeds(self, source, sample_aoi, sleeps):
        responses.add(responses.POST, BASE_URL, json={}, status=429)
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_happy.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.OK
        assert len(responses.calls) == 2
        assert sleeps == [1.0]

    @responses.activate
    def test_504_is_retried(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json={}, status=504)
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_empty.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.EMPTY
        assert len(responses.calls) == 2

    @responses.activate
    def test_exhausts_retries_then_reports_error(self, source, sample_aoi, sleeps):
        responses.add(responses.POST, BASE_URL, json={}, status=429)
        responses.add(responses.POST, BASE_URL, json={}, status=429)
        responses.add(responses.POST, BASE_URL, json={}, status=429)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert len(responses.calls) == 3  # MAX_ATTEMPTS, no more
        assert sleeps == [1.0, 2.0]

    @responses.activate
    def test_500_is_not_retried(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, json={}, status=500)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
        assert len(responses.calls) == 1

    @responses.activate
    def test_timeout_is_retried(self, source, sample_aoi):
        responses.add(responses.POST, BASE_URL, body=requests.exceptions.Timeout())
        responses.add(responses.POST, BASE_URL, json=load_fixture("overpass_health_empty.json"), status=200)
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.EMPTY
        assert len(responses.calls) == 2

    @responses.activate
    def test_unmocked_request_is_handled_gracefully(self, source, sample_aoi):
        result = source.fetch(sample_aoi)
        assert result.status is SourceStatus.ERROR
