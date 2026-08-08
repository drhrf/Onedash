from __future__ import annotations

import json
from pathlib import Path

import pytest

from onedash.datasources.base import AreaOfInterest, DataSource, FetchResult, SourceStatus

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_aoi() -> AreaOfInterest:
    return AreaOfInterest(lat=-22.8894, lon=-42.0286, radius_km=25.0, label="Cabo Frio")


class FakeDataSource(DataSource):
    source_id = "fake"
    display_name_pt = "Fonte de teste"

    def __init__(self, *args, result=None, raise_error=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._result = result
        self._raise_error = raise_error

    def _fetch(self, aoi, params):
        if self._raise_error is not None:
            raise self._raise_error
        if self._result is not None:
            return self._result
        return FetchResult(source_id=self.source_id, status=SourceStatus.OK, fetched_at=self._clock())


@pytest.fixture
def fake_data_source_cls():
    return FakeDataSource
