from __future__ import annotations

from datetime import datetime, timezone

import plotly.graph_objects as go
import pytest

from onedash.datasources.base import FetchResult, GeoRecord, SourceStatus
from onedash.map_builder import build_figure
from onedash.layer_registry import get_layer

FETCHED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

WEATHER = "open_meteo_weather"
HEALTH = "overpass_health"


def _record(lat=-22.88, lon=-42.02, label="ponto"):
    return GeoRecord(id="1", lat=lat, lon=lon, label=label)


def _ok(source_id, records, observation_time=None):
    return FetchResult(
        source_id=source_id, status=SourceStatus.OK, records=records,
        observation_time=observation_time, fetched_at=FETCHED_AT,
    )


def _error(source_id, message="deu ruim"):
    return FetchResult(source_id=source_id, status=SourceStatus.ERROR, fetched_at=FETCHED_AT, error_message=message)


def _empty(source_id):
    return FetchResult(source_id=source_id, status=SourceStatus.EMPTY, fetched_at=FETCHED_AT)


def _unsupported(source_id, message="não disponível aqui"):
    return FetchResult(
        source_id=source_id, status=SourceStatus.UNSUPPORTED_LOCATION, fetched_at=FETCHED_AT, error_message=message
    )


def _data_trace_count(figure: go.Figure) -> int:
    """Counts traces that actually carry points, excluding the invisible
    placeholder trace build_figure adds so Plotly still renders the `map`
    subplot (tiles, pan/zoom) when no real data layer is active — without
    at least one map-type trace, Plotly silently falls back to a generic
    Cartesian axes plot instead of a map, which a bare `len(figure.data)`
    check can't tell apart from "correctly showing an empty map"."""
    return sum(1 for trace in figure.data if len(trace.lat) > 0)


class TestBuildFigureBasics:
    def test_zero_layers_returns_base_map_with_no_data_traces(self):
        result = build_figure(-22.88, -42.02, {})
        assert isinstance(result.figure, go.Figure)
        assert _data_trace_count(result.figure) == 0
        assert result.warnings == []

    def test_zero_layers_still_has_a_map_type_trace_so_the_map_renders(self):
        # Regression test: a figure with zero traces of any kind causes
        # Plotly to render a generic Cartesian scatter plot instead of a
        # map (confirmed visually — see M9 manual checkpoint). There must
        # always be at least one Scattermap-family trace present.
        result = build_figure(-22.88, -42.02, {})
        assert len(result.figure.data) >= 1
        assert result.figure.data[-1].type == "scattermap"

    def test_single_layer_produces_one_data_trace(self):
        result = build_figure(-22.88, -42.02, {WEATHER: _ok(WEATHER, [_record()])})
        assert _data_trace_count(result.figure) == 1
        assert result.warnings == []

    def test_multiple_layers_produce_multiple_data_traces(self):
        results = {WEATHER: _ok(WEATHER, [_record()]), HEALTH: _ok(HEALTH, [_record(label="hospital")])}
        result = build_figure(-22.88, -42.02, results)
        assert _data_trace_count(result.figure) == 2

    def test_trace_uses_layer_color_and_label(self):
        result = build_figure(-22.88, -42.02, {WEATHER: _ok(WEATHER, [_record()])})
        trace = result.figure.data[0]
        layer = get_layer(WEATHER)
        assert trace.marker.color == layer.color
        assert trace.name == layer.label_pt

    def test_trace_uses_record_label_as_hover_text(self):
        result = build_figure(-22.88, -42.02, {WEATHER: _ok(WEATHER, [_record(label="22.5 °C")])})
        assert "22.5 °C" in result.figure.data[0].text

    def test_map_center_and_zoom_are_set(self):
        result = build_figure(-22.88, -42.02, {}, zoom=12)
        map_layout = result.figure.layout.map
        assert map_layout.center.lat == -22.88
        assert map_layout.center.lon == -42.02
        assert map_layout.zoom == 12


class TestBuildFigureStatusHandling:
    def test_error_status_excluded_from_traces_but_in_warnings(self):
        result = build_figure(-22.88, -42.02, {WEATHER: _error(WEATHER, "API fora do ar")})
        assert _data_trace_count(result.figure) == 0
        assert any("API fora do ar" in w for w in result.warnings)

    def test_empty_status_produces_warning_not_trace(self):
        result = build_figure(-22.88, -42.02, {HEALTH: _empty(HEALTH)})
        assert _data_trace_count(result.figure) == 0
        assert len(result.warnings) == 1

    def test_unsupported_location_produces_distinct_warning(self):
        result = build_figure(-22.88, -42.02, {"infodengue": _unsupported("infodengue", "fora da região")})
        assert _data_trace_count(result.figure) == 0
        assert any("fora da região" in w for w in result.warnings)

    def test_empty_and_error_produce_distinguishable_messages(self):
        result = build_figure(
            -22.88, -42.02, {WEATHER: _error(WEATHER, "falha real"), HEALTH: _empty(HEALTH)}
        )
        assert len(result.warnings) == 2
        assert result.warnings[0] != result.warnings[1]

    def test_unknown_layer_id_produces_warning_not_crash(self):
        result = build_figure(-22.88, -42.02, {"nao_existe": _ok("nao_existe", [_record()])})
        assert _data_trace_count(result.figure) == 0
        assert len(result.warnings) == 1

    def test_mixed_ok_and_error_layers(self):
        results = {WEATHER: _ok(WEATHER, [_record()]), HEALTH: _error(HEALTH, "falhou")}
        result = build_figure(-22.88, -42.02, results)
        assert _data_trace_count(result.figure) == 1
        assert len(result.warnings) == 1


class TestBuildFigureCoordinateFiltering:
    def test_records_missing_coordinates_are_silently_dropped_when_others_are_valid(self):
        records = [_record(lat=None, lon=None), _record()]
        result = build_figure(-22.88, -42.02, {WEATHER: _ok(WEATHER, records)})
        assert _data_trace_count(result.figure) == 1
        assert result.warnings == []

    def test_all_records_missing_coordinates_produces_warning_not_empty_trace(self):
        records = [_record(lat=None, lon=None)]
        result = build_figure(-22.88, -42.02, {WEATHER: _ok(WEATHER, records)})
        assert _data_trace_count(result.figure) == 0
        assert len(result.warnings) == 1
