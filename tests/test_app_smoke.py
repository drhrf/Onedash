from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from streamlit.testing.v1 import AppTest

from onedash.datasources.base import FetchResult, SourceStatus
from onedash.datasources.open_meteo_geocoding import GeocodeMatch, GeocodeSearchResult

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
FETCHED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_app() -> AppTest:
    return AppTest.from_file(APP_PATH)


def _ok_result(source_id: str = "open_meteo_weather") -> FetchResult:
    return FetchResult(source_id=source_id, status=SourceStatus.OK, records=[], fetched_at=FETCHED_AT)


class TestAppBasics:
    def test_app_runs_without_exception(self):
        at = _make_app()
        at.run(timeout=15)
        assert not at.exception

    def test_app_renders_one_plotly_chart(self):
        at = _make_app()
        at.run(timeout=15)
        assert len(at.get("plotly_chart")) == 1

    def test_default_run_has_no_layers_selected(self):
        at = _make_app()
        at.run(timeout=15)
        assert at.multiselect[0].value == []

    def test_default_run_shows_no_layers_info_message(self):
        at = _make_app()
        at.run(timeout=15)
        assert len(at.info) == 1

    def test_default_location_is_cabo_frio(self):
        at = _make_app()
        at.run(timeout=15)
        assert "Cabo Frio" in at.sidebar.caption[0].value


class TestLayerSelection:
    def test_selecting_a_layer_clears_the_info_message(self, monkeypatch):
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: _ok_result())
        at = _make_app()
        at.run(timeout=15)
        at.multiselect[0].select("open_meteo_weather").run(timeout=15)
        assert not at.exception
        assert len(at.info) == 0

    def test_error_status_surfaces_as_warning_not_exception(self, monkeypatch):
        error_result = FetchResult(
            source_id="open_meteo_weather",
            status=SourceStatus.ERROR,
            fetched_at=FETCHED_AT,
            error_message="falha simulada",
        )
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: error_result)
        at = _make_app()
        at.run(timeout=15)
        at.multiselect[0].select("open_meteo_weather").run(timeout=15)
        assert not at.exception
        assert any("falha simulada" in w.value for w in at.warning)

    def test_switching_layers_back_and_forth_never_raises(self, monkeypatch):
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: _ok_result())
        at = _make_app()
        at.run(timeout=15)
        at.multiselect[0].select("open_meteo_weather").run(timeout=15)
        assert not at.exception
        at.multiselect[0].select("overpass_health").run(timeout=15)
        assert not at.exception
        at.multiselect[0].unselect("open_meteo_weather").run(timeout=15)
        assert not at.exception
        at.multiselect[0].unselect("overpass_health").run(timeout=15)
        assert not at.exception
        assert len(at.info) == 1  # back to zero layers selected

    def test_selecting_all_layers_never_raises(self, monkeypatch):
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: _ok_result())
        at = _make_app()
        at.run(timeout=15)
        for layer_id in (
            "open_meteo_weather",
            "open_meteo_air_quality",
            "open_meteo_marine",
            "overpass_health",
            "infodengue",
        ):
            at.multiselect[0].select(layer_id).run(timeout=15)
        assert not at.exception


class TestFreshnessBadges:
    def test_badge_shows_both_data_age_and_checked_time(self, monkeypatch):
        # observation_time and fetched_at are deliberately different here:
        # a cached-but-stale result must not read as "fresh" just because
        # it was checked recently (the whole point of the time-lag feature).
        observation_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        fetched_at = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
        result = FetchResult(
            source_id="open_meteo_weather",
            status=SourceStatus.OK,
            records=[],
            observation_time=observation_time,
            fetched_at=fetched_at,
        )
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: result)

        at = _make_app()
        at.run(timeout=15)
        at.multiselect[0].select("open_meteo_weather").run(timeout=15)

        assert not at.exception
        caption_text = " ".join(c.value for c in at.caption)
        assert "verificado" in caption_text
        assert "Clima atual" in caption_text

    def test_no_badge_shown_when_no_layer_is_ok(self, monkeypatch):
        error_result = FetchResult(
            source_id="open_meteo_weather", status=SourceStatus.ERROR, fetched_at=FETCHED_AT, error_message="x"
        )
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: error_result)
        at = _make_app()
        at.run(timeout=15)
        at.multiselect[0].select("open_meteo_weather").run(timeout=15)
        assert not at.exception
        assert not any("verificado" in c.value for c in at.caption)


class TestLocationSearch:
    def test_search_with_a_match_updates_current_location(self, monkeypatch):
        result = GeocodeSearchResult(
            query="Buzios",
            matches=[
                GeocodeMatch(
                    name="Armação dos Búzios", lat=-22.7469, lon=-41.8817, country="Brasil", admin1="Rio de Janeiro"
                )
            ],
        )
        monkeypatch.setattr("onedash.ui.sidebar.search_locations", lambda *a, **k: result)
        at = _make_app()
        at.run(timeout=15)
        at.sidebar.text_input[0].set_value("Buzios").run(timeout=15)
        at.sidebar.button[0].click().run(timeout=15)
        assert not at.exception
        assert "Búzios" in at.sidebar.caption[0].value

    def test_search_with_no_results_shows_warning_and_keeps_default_location(self, monkeypatch):
        result = GeocodeSearchResult(query="xyzxyz", matches=[])
        monkeypatch.setattr("onedash.ui.sidebar.search_locations", lambda *a, **k: result)
        at = _make_app()
        at.run(timeout=15)
        at.sidebar.text_input[0].set_value("xyzxyz").run(timeout=15)
        at.sidebar.button[0].click().run(timeout=15)
        assert not at.exception
        assert len(at.sidebar.warning) == 1
        assert "Cabo Frio" in at.sidebar.caption[0].value

    def test_search_failure_shows_error_not_exception(self, monkeypatch):
        result = GeocodeSearchResult(query="falha", matches=[], error_message="falha de rede")
        monkeypatch.setattr("onedash.ui.sidebar.search_locations", lambda *a, **k: result)
        at = _make_app()
        at.run(timeout=15)
        at.sidebar.text_input[0].set_value("falha").run(timeout=15)
        at.sidebar.button[0].click().run(timeout=15)
        assert not at.exception
        assert len(at.sidebar.error) == 1

    def test_empty_query_does_not_search(self, monkeypatch):
        calls = []
        monkeypatch.setattr("onedash.ui.sidebar.search_locations", lambda *a, **k: calls.append(1))
        at = _make_app()
        at.run(timeout=15)
        at.sidebar.button[0].click().run(timeout=15)
        assert not at.exception
        assert calls == []


class TestGridResize:
    def test_panel_count_controls_number_of_panels_rendered(self, monkeypatch):
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: _ok_result())
        at = _make_app()
        at.run(timeout=15)
        assert len(at.multiselect) == 1  # default panel count is 1

        at.sidebar.select_slider[0].set_value(4).run(timeout=15)
        assert not at.exception
        assert len(at.multiselect) == 4

        at.sidebar.select_slider[0].set_value(6).run(timeout=15)
        assert not at.exception
        assert len(at.multiselect) == 6

    def test_resize_sequence_never_raises_and_preserves_panel_zero_state(self, monkeypatch):
        # Regression coverage for the fixed-absolute-widget-key design
        # (grid_layout.compute_rows always assigns panel 0 the same index
        # regardless of N): panel 0's layer selection must survive being
        # shrunk and grown repeatedly, and no step should raise
        # Streamlit's DuplicateWidgetID-style error.
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: _ok_result())
        at = _make_app()
        at.run(timeout=15)

        at.multiselect[0].select("open_meteo_weather").run(timeout=15)
        assert not at.exception
        assert at.multiselect[0].value == ["open_meteo_weather"]

        for target_count in (4, 6, 2, 1, 6):
            at.sidebar.select_slider[0].set_value(target_count).run(timeout=15)
            assert not at.exception, f"resize to {target_count} raised: {list(at.exception)}"
            assert len(at.multiselect) == target_count
            assert at.multiselect[0].value == ["open_meteo_weather"], (
                f"panel 0 lost its selection after resizing to {target_count}"
            )

    def test_each_panel_has_independent_layer_selection(self, monkeypatch):
        monkeypatch.setattr("onedash.ui.panel.fetch_layer", lambda *a, **k: _ok_result())
        at = _make_app()
        at.run(timeout=15)
        at.sidebar.select_slider[0].set_value(3).run(timeout=15)

        at.multiselect[0].select("open_meteo_weather").run(timeout=15)
        at.multiselect[1].select("overpass_health").run(timeout=15)

        assert at.multiselect[0].value == ["open_meteo_weather"]
        assert at.multiselect[1].value == ["overpass_health"]
        assert at.multiselect[2].value == []
