from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from onedash.datasources.base import FetchResult, GeoRecord, SourceStatus
from onedash.layer_registry import get_layer
from onedash.summaries import FRESHNESS_COLOR, freshness_line, summarize_records

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

WEATHER = "open_meteo_weather"  # freshness_profile="weather": fresh <=2h, stale >12h
HEALTH = "overpass_health"  # freshness_profile="osm_facility": fresh <=90d, stale >2y


def _result(source_id, records=(), observation_time=None, fetched_at=NOW, status=SourceStatus.OK):
    return FetchResult(
        source_id=source_id,
        status=status,
        records=list(records),
        observation_time=observation_time,
        fetched_at=fetched_at,
    )


def _record(label="ponto", lat=-22.88, lon=-42.02, record_id="1"):
    return GeoRecord(id=record_id, lat=lat, lon=lon, label=label)


class TestSummarizeRecords:
    def test_no_records_gives_empty_string(self):
        assert summarize_records(_result(WEATHER), get_layer(WEATHER)) == ""

    def test_single_record_uses_its_own_label(self):
        result = _result(WEATHER, [_record(label="24.3 °C")])
        assert summarize_records(result, get_layer(WEATHER)) == "24.3 °C"

    def test_many_records_are_counted_with_the_layer_noun(self):
        result = _result(HEALTH, [_record(record_id=str(i)) for i in range(12)])
        assert summarize_records(result, get_layer(HEALTH)) == "12 estabelecimentos"

    def test_single_record_without_a_label_falls_back_to_the_count(self):
        # GeoRecord.label defaults to "", so a source that omits it must not
        # produce a dangling "Clima atual:  — dado de ..." with a hole in it.
        result = _result(WEATHER, [_record(label="")])
        assert summarize_records(result, get_layer(WEATHER)) == "1 medições"

    def test_two_records_are_counted_not_labeled(self):
        result = _result(HEALTH, [_record(label="Hospital A", record_id="a"), _record(label="Hospital B", record_id="b")])
        assert summarize_records(result, get_layer(HEALTH)) == "2 estabelecimentos"


class TestFreshnessLine:
    def test_fresh_data_is_green(self):
        result = _result(WEATHER, [_record(label="24.3 °C")], observation_time=NOW - timedelta(minutes=30))
        line = freshness_line(get_layer(WEATHER), result, now=NOW)
        assert line.startswith(":green[●]")
        assert "**Clima atual**" in line
        assert "24.3 °C" in line
        assert "há 30 min" in line

    def test_aging_data_is_orange(self):
        result = _result(WEATHER, observation_time=NOW - timedelta(hours=6))
        assert freshness_line(get_layer(WEATHER), result, now=NOW).startswith(":orange[●]")

    def test_stale_data_is_red(self):
        result = _result(WEATHER, observation_time=NOW - timedelta(days=3))
        assert freshness_line(get_layer(WEATHER), result, now=NOW).startswith(":red[●]")

    def test_unknown_observation_time_is_gray_and_still_shown(self):
        line = freshness_line(get_layer(WEATHER), _result(WEATHER), now=NOW)
        assert line.startswith(":gray[●]")
        assert "idade desconhecida" in line

    def test_data_age_and_check_time_are_both_shown_and_differ(self):
        # The whole point of the feature: a result fetched a moment ago from
        # cache must still report the true age of the underlying observation.
        result = _result(
            WEATHER,
            [_record(label="19.0 °C")],
            observation_time=NOW - timedelta(hours=20),
            fetched_at=NOW - timedelta(minutes=2),
        )
        line = freshness_line(get_layer(WEATHER), result, now=NOW)
        assert "dado de há 20 h" in line
        assert "verificado há 2 min" in line
        assert line.startswith(":red[●]")  # 20h old weather is stale...
        assert "há 2 min" in line  # ...even though it was just checked

    def test_profile_comes_from_the_layers_own_source(self):
        # 6 months old: stale for weather, merely aging for a facility registry.
        observed = NOW - timedelta(days=180)
        weather_line = freshness_line(get_layer(WEATHER), _result(WEATHER, observation_time=observed), now=NOW)
        health_line = freshness_line(get_layer(HEALTH), _result(HEALTH, observation_time=observed), now=NOW)
        assert weather_line.startswith(":red[●]")
        assert health_line.startswith(":orange[●]")

    def test_line_has_no_empty_value_segment_when_there_are_no_records(self):
        line = freshness_line(get_layer(WEATHER), _result(WEATHER, observation_time=NOW), now=NOW)
        assert " —  " not in line
        assert "**Clima atual**: dado de" in line

    def test_future_observation_time_is_flagged_not_negative(self):
        result = _result(WEATHER, observation_time=NOW + timedelta(hours=1))
        line = freshness_line(get_layer(WEATHER), result, now=NOW)
        assert line.startswith(":gray[●]")
        assert "futuro" in line

    @pytest.mark.parametrize("level", list(FRESHNESS_COLOR))
    def test_every_freshness_level_has_a_color(self, level):
        assert FRESHNESS_COLOR[level]
