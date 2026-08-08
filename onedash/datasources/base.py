from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import requests
from pydantic import BaseModel, Field, field_validator

from onedash import geo_utils


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"  # query succeeded, legitimately zero records
    ERROR = "error"  # HTTP/timeout/malformed — never raised into the UI
    UNSUPPORTED_LOCATION = "unsupported_location"  # e.g. InfoDengue outside Brazil


class GeoRecord(BaseModel):
    id: str
    lat: float | None = None
    lon: float | None = None
    value: float | None = None
    label: str = ""
    observation_time: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("lat")
    @classmethod
    def _validate_lat(cls, v: float | None) -> float | None:
        if not geo_utils.in_range_or_none(v, -90.0, 90.0):
            raise ValueError(f"lat out of range: {v!r}")
        return v

    @field_validator("lon")
    @classmethod
    def _validate_lon(cls, v: float | None) -> float | None:
        if not geo_utils.in_range_or_none(v, -180.0, 180.0):
            raise ValueError(f"lon out of range: {v!r}")
        return v

    @field_validator("observation_time")
    @classmethod
    def _validate_observation_time(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        return v


class FetchResult(BaseModel):
    source_id: str
    status: SourceStatus
    records: list[GeoRecord] = Field(default_factory=list)
    observation_time: datetime | None = None  # source-level "as-of" time, for the freshness badge
    fetched_at: datetime  # tz-aware; injected via a clock function so it's testable
    error_message: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observation_time")
    @classmethod
    def _validate_observation_time(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        return v

    @field_validator("fetched_at")
    @classmethod
    def _validate_fetched_at(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")
        return v


class AreaOfInterest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 25.0
    label: str = ""

    @field_validator("lat")
    @classmethod
    def _validate_lat(cls, v: float) -> float:
        if not geo_utils.in_range_or_none(v, -90.0, 90.0):
            raise ValueError(f"lat out of range: {v!r}")
        return v

    @field_validator("lon")
    @classmethod
    def _validate_lon(cls, v: float) -> float:
        if not geo_utils.in_range_or_none(v, -180.0, 180.0):
            raise ValueError(f"lon out of range: {v!r}")
        return v

    @field_validator("radius_km")
    @classmethod
    def _validate_radius(cls, v: float) -> float:
        if not v > 0:
            raise ValueError(f"radius_km must be positive: {v!r}")
        return v

    def to_bbox(self) -> tuple[float, float, float, float]:
        return geo_utils.bbox_from_radius(self.lat, self.lon, self.radius_km)


class DataSource(ABC):
    source_id: str = ""
    display_name_pt: str = ""
    freshness_profile: str = "default"
    requires_api_key: bool = False

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 10.0,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout
        self._clock = clock

    def fetch(self, aoi: AreaOfInterest, params: dict[str, Any] | None = None) -> FetchResult:
        """Template method. This except-Exception is a last-resort safety net
        so one bad source can never crash the app — subclasses still catch
        their own known failure modes (HTTP errors, timeouts, bad JSON) for
        specific, useful error messages."""
        try:
            return self._fetch(aoi, params or {})
        except Exception as exc:  # noqa: BLE001 — intentional last-resort net
            return FetchResult(
                source_id=self.source_id,
                status=SourceStatus.ERROR,
                fetched_at=self._clock(),
                error_message=f"erro inesperado: {exc}",
            )

    @abstractmethod
    def _fetch(self, aoi: AreaOfInterest, params: dict[str, Any]) -> FetchResult: ...
