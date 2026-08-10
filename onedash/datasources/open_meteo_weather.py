from __future__ import annotations

from typing import Any

import requests

from onedash import geo_utils
from onedash.datasources.base import AreaOfInterest, DataSource, FetchResult, GeoRecord

BASE_URL = "https://api.open-meteo.com/v1/forecast"

CURRENT_VARS = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,"
    "precipitation,weather_code,wind_speed_10m,wind_direction_10m"
)


class OpenMeteoWeatherSource(DataSource):
    source_id = "open_meteo_weather"
    display_name_pt = "Clima atual (Open-Meteo)"
    freshness_profile = "weather"

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
            return self._error("tempo de resposta esgotado ao consultar a API de clima (Open-Meteo)")
        except requests.exceptions.ConnectionError:
            return self._error("falha de conexão ao consultar a API de clima (Open-Meteo)")
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "desconhecido"
            return self._error(f"erro HTTP {status_code} da API de clima (Open-Meteo)")
        except requests.exceptions.RequestException as exc:
            return self._error(f"erro ao consultar a API de clima (Open-Meteo): {exc}")

        try:
            payload = response.json()
        except ValueError:
            return self._error("resposta inválida (JSON malformado) da API de clima (Open-Meteo)")

        current = payload.get("current")
        if not current:
            return self._empty()

        try:
            observation_time = geo_utils.parse_iso8601_utc(current["time"], assume_utc_if_naive=True)
            temperature = float(current["temperature_2m"])
        except (KeyError, TypeError, ValueError):
            return self._error("resposta da API de clima (Open-Meteo) não contém os campos esperados")

        record = GeoRecord(
            id=f"open_meteo_weather:{aoi.lat:.4f},{aoi.lon:.4f}",
            lat=aoi.lat,
            lon=aoi.lon,
            value=temperature,
            label=f"{temperature:.1f} °C",
            observation_time=observation_time,
            raw=current,
        )
        return self._ok([record], observation_time=observation_time)
