from __future__ import annotations

from typing import Any

import requests

from onedash import geo_utils
from onedash.datasources.base import AreaOfInterest, DataSource, FetchResult, GeoRecord

BASE_URL = "https://marine-api.open-meteo.com/v1/marine"

# Sea surface temperature is directly relevant to the Cabo Frio upwelling
# (ressurgência) — a well-known local cold-water phenomenon — but its exact
# availability/field name could not be verified live (network-restricted
# sandbox); it's requested optimistically and simply omitted from the record
# if the upstream response doesn't include it, rather than failing the fetch.
CURRENT_VARS = "wave_height,wave_period,wave_direction,sea_surface_temperature"


class OpenMeteoMarineSource(DataSource):
    source_id = "open_meteo_marine"
    display_name_pt = "Condições marítimas (Open-Meteo)"
    freshness_profile = "marine"

    def _fetch(self, aoi: AreaOfInterest, params: dict[str, Any]) -> FetchResult:
        query = {
            "latitude": aoi.lat,
            "longitude": aoi.lon,
            "current": CURRENT_VARS,
            "timezone": "UTC",
        }
        try:
            response = self._session.get(BASE_URL, params=query, timeout=self._timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            return self._error("tempo de resposta esgotado ao consultar a API marítima")
        except requests.exceptions.ConnectionError:
            return self._error("falha de conexão ao consultar a API marítima")
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "desconhecido"
            return self._error(f"erro HTTP {status_code} da API marítima")
        except requests.exceptions.RequestException as exc:
            return self._error(f"erro ao consultar a API marítima: {exc}")

        try:
            payload = response.json()
        except ValueError:
            return self._error("resposta inválida (JSON malformado) da API marítima")

        current = payload.get("current")
        if not current:
            return self._empty()

        try:
            observation_time = geo_utils.parse_iso8601_utc(current["time"], assume_utc_if_naive=True)
            wave_height = float(current["wave_height"])
        except (KeyError, TypeError, ValueError):
            return self._error("resposta da API marítima não contém os campos esperados")

        label = f"Altura das ondas: {wave_height:.1f} m"
        sea_surface_temperature = current.get("sea_surface_temperature")
        if isinstance(sea_surface_temperature, (int, float)):
            label += f" · TSM: {sea_surface_temperature:.1f} °C"

        record = GeoRecord(
            id=f"open_meteo_marine:{aoi.lat:.4f},{aoi.lon:.4f}",
            lat=aoi.lat,
            lon=aoi.lon,
            value=wave_height,
            label=label,
            observation_time=observation_time,
            raw=current,
        )
        return self._ok([record], observation_time=observation_time)
