from __future__ import annotations

import time
from typing import Any, Callable

import requests
from pydantic import ValidationError

from onedash import config, freshness, geo_utils
from onedash.datasources.base import AreaOfInterest, DataSource, FetchResult, GeoRecord

BASE_URL = "https://overpass-api.de/api/interpreter"

AMENITIES = ("hospital", "clinic", "doctors", "pharmacy")

AMENITY_LABELS_PT = {
    "hospital": "Hospital",
    "clinic": "Clínica",
    "doctors": "Consultório médico",
    "pharmacy": "Farmácia",
}

RETRYABLE_STATUS_CODES = {429, 504}
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (1.0, 2.0)  # waited before attempt 2 and attempt 3


class OverpassHealthSource(DataSource):
    source_id = "overpass_health"
    display_name_pt = "Estabelecimentos de saúde (OpenStreetMap)"
    freshness_profile = "osm_facility"

    def __init__(self, *args: Any, sleep: Callable[[float], None] = time.sleep, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._sleep = sleep

    def _fetch(self, aoi: AreaOfInterest, params: dict[str, Any]) -> FetchResult:
        if aoi.radius_km > config.OVERPASS_MAX_RADIUS_KM:
            return self._error(
                f"raio de busca ({aoi.radius_km:.0f} km) maior que o máximo permitido "
                f"({config.OVERPASS_MAX_RADIUS_KM:.0f} km) para estabelecimentos de saúde"
            )

        south, west, north, east = aoi.to_bbox()
        query = self._build_query(south, west, north, east)

        response, error = self._post_with_retry(query)
        if response is None:
            return self._error(error)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            return self._error(f"erro HTTP {response.status_code} do Overpass (OpenStreetMap)")

        try:
            payload = response.json()
        except ValueError:
            return self._error("resposta inválida (JSON malformado) do Overpass (OpenStreetMap)")

        elements = payload.get("elements")
        if elements is None:
            return self._error("resposta do Overpass (OpenStreetMap) não contém os campos esperados")
        if not elements:
            return self._empty()

        records = [r for r in (self._parse_element(e) for e in elements) if r is not None]
        if not records:
            return self._empty()

        observation_time = freshness.aggregate_observation_time([r.observation_time for r in records])
        return self._ok(records, observation_time=observation_time)

    def _post_with_retry(self, query: str) -> tuple[requests.Response | None, str | None]:
        last_error = None
        for attempt in range(MAX_ATTEMPTS):
            if attempt > 0:
                self._sleep(RETRY_BACKOFF_SECONDS[attempt - 1])
            try:
                response = self._session.post(BASE_URL, data={"data": query}, timeout=self._timeout)
            except requests.exceptions.Timeout:
                last_error = "tempo de resposta esgotado ao consultar o Overpass (OpenStreetMap)"
                continue
            except requests.exceptions.ConnectionError:
                last_error = "falha de conexão ao consultar o Overpass (OpenStreetMap)"
                continue
            except requests.exceptions.RequestException as exc:
                return None, f"erro ao consultar o Overpass (OpenStreetMap): {exc}"

            if response.status_code in RETRYABLE_STATUS_CODES:
                last_error = f"Overpass (OpenStreetMap) sobrecarregado (HTTP {response.status_code})"
                continue

            return response, None

        return None, last_error or "falha ao consultar o Overpass (OpenStreetMap)"

    def _parse_element(self, element: dict) -> GeoRecord | None:
        lat = element.get("lat")
        lon = element.get("lon")
        osm_id = element.get("id")
        if lat is None or lon is None or osm_id is None:
            return None  # e.g. a way/relation without a resolved center point — skip, don't crash

        tags = element.get("tags") or {}
        amenity = tags.get("amenity", "")
        name = tags.get("name") or AMENITY_LABELS_PT.get(amenity, amenity or "Estabelecimento de saúde")

        observation_time = None
        timestamp = element.get("timestamp")
        if timestamp:
            try:
                observation_time = geo_utils.parse_iso8601_utc(timestamp)
            except ValueError:
                observation_time = None

        try:
            return GeoRecord(
                id=f"osm:{element.get('type', 'node')}:{osm_id}",
                lat=float(lat),
                lon=float(lon),
                label=name,
                observation_time=observation_time,
                raw=tags,
            )
        except (ValidationError, TypeError, ValueError):
            return None  # invalid coordinates from upstream — skip this record, don't fail the whole layer

    @staticmethod
    def _build_query(south: float, west: float, north: float, east: float) -> str:
        bbox = f"{south},{west},{north},{east}"
        clauses = "\n".join(f'  node["amenity"="{amenity}"]({bbox});' for amenity in AMENITIES)
        return f"[out:json][timeout:25];\n(\n{clauses}\n);\nout meta;"
