from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_runs_without_exception():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=15)
    assert not at.exception


def test_app_renders_one_plotly_chart():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=15)
    assert len(at.get("plotly_chart")) == 1
