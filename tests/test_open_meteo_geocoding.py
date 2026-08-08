from __future__ import annotations

import pytest
import requests
import responses

from onedash.datasources.open_meteo_geocoding import BASE_URL, search_locations
from tests.conftest import load_fixture


class TestSearchLocations:
    @responses.activate
    def test_happy_path_returns_matches(self):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_geocoding_happy.json"), status=200)
        result = search_locations("Cabo Frio")
        assert result.ok
        assert len(result.matches) == 2
        assert result.matches[0].name == "Cabo Frio"
        assert result.matches[0].lat == pytest.approx(-22.8894)

    @responses.activate
    def test_display_label_combines_fields(self):
        responses.add(responses.GET, BASE_URL, json=load_fixture("open_meteo_geocoding_happy.json"), status=200)
        result = search_locations("Cabo Frio")
        assert result.matches[0].display_label == "Cabo Frio, Rio de Janeiro, Brasil"

    @responses.activate
    def test_no_results_is_ok_with_empty_matches(self):
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_geocoding_no_results.json"), status=200
        )
        result = search_locations("xyzxyzxyz-nonexistent-place")
        assert result.ok
        assert result.matches == []

    @responses.activate
    def test_one_malformed_result_is_skipped_not_fatal(self):
        responses.add(
            responses.GET,
            BASE_URL,
            json=load_fixture("open_meteo_geocoding_one_malformed_result.json"),
            status=200,
        )
        result = search_locations("Cabo")
        assert result.ok
        assert len(result.matches) == 1
        assert result.matches[0].name == "Cabo Frio"

    def test_empty_query_returns_no_matches_without_http_call(self):
        result = search_locations("   ")
        assert result.ok
        assert result.matches == []

    @responses.activate
    def test_special_characters_in_query_do_not_crash(self):
        responses.add(
            responses.GET, BASE_URL, json=load_fixture("open_meteo_geocoding_no_results.json"), status=200
        )
        result = search_locations("São Pedro d'Aldeia & Cia? 100%")
        assert result.ok

    @responses.activate
    def test_timeout_is_reported_as_error(self):
        responses.add(responses.GET, BASE_URL, body=requests.exceptions.Timeout())
        result = search_locations("Cabo Frio")
        assert not result.ok
        assert result.matches == []

    @responses.activate
    def test_http_error_is_reported(self):
        responses.add(responses.GET, BASE_URL, json={}, status=503)
        result = search_locations("Cabo Frio")
        assert not result.ok

    @responses.activate
    def test_malformed_json_is_reported(self):
        responses.add(responses.GET, BASE_URL, body="not json", status=200)
        result = search_locations("Cabo Frio")
        assert not result.ok
