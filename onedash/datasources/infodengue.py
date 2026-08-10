from __future__ import annotations

from datetime import timedelta
from typing import Any

import requests

from onedash import br_municipalities, geo_utils
from onedash.datasources.base import AreaOfInterest, DataSource, FetchResult, GeoRecord

BASE_URL = "https://info.dengue.mat.br/api/alertcity"

# Request parameters confirmed against InfoDengue's own API docs
# (info.dengue.mat.br/services/api/doc): geocode, disease, format, ew_start,
# ew_end, ey_start, ey_end are all mandatory. The RESPONSE schema below
# (SE/data_iniSE/casos_est/casos) reflects the AlertaDengue/InfoDengue
# project's documented data dictionary from general knowledge, not a live
# response capture (this sandbox's network policy blocks a live hit) —
# parsing is defensive and fails to a clean ERROR/EMPTY result rather than
# crashing if the real shape differs in some field.
DISEASE_LABELS_PT = {"dengue": "Dengue", "chikungunya": "Chikungunya", "zika": "Zika"}

WINDOW_WEEKS = 8
PRELIMINARY_WINDOW_WEEKS = 3  # InfoDengue documents recent weeks as preliminary/revised


class InfoDengueSource(DataSource):
    source_id = "infodengue"
    display_name_pt = "Vigilância de arboviroses (InfoDengue)"
    freshness_profile = "epidemiological"

    def _fetch(self, aoi: AreaOfInterest, params: dict[str, Any]) -> FetchResult:
        municipality = br_municipalities.find_nearest(aoi.lat, aoi.lon)
        if municipality is None:
            return self._unsupported_location(
                "dados do InfoDengue disponíveis apenas para municípios da Região dos Lagos neste protótipo"
            )

        disease = params.get("disease", "dengue")
        if disease not in DISEASE_LABELS_PT:
            return self._error(f"doença inválida: {disease!r} (use dengue, chikungunya ou zika)")

        now = self._clock()
        end_year, end_week = _epidemiological_week(now)
        start_year, start_week = _epidemiological_week(now - timedelta(weeks=WINDOW_WEEKS))

        query = {
            "geocode": municipality.ibge_code,
            "disease": disease,
            "format": "json",
            "ew_start": start_week,
            "ew_end": end_week,
            "ey_start": start_year,
            "ey_end": end_year,
        }
        try:
            response = self._session.get(BASE_URL, params=query, timeout=self._timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            return self._error("tempo de resposta esgotado ao consultar o InfoDengue")
        except requests.exceptions.ConnectionError:
            return self._error("falha de conexão ao consultar o InfoDengue")
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "desconhecido"
            return self._error(f"erro HTTP {status_code} do InfoDengue")
        except requests.exceptions.RequestException as exc:
            return self._error(f"erro ao consultar o InfoDengue: {exc}")

        try:
            payload = response.json()
        except ValueError:
            return self._error("resposta inválida (JSON malformado) do InfoDengue")

        if not isinstance(payload, list):
            return self._error("resposta do InfoDengue em formato inesperado")
        if not payload:
            return self._empty()

        try:
            latest = max(payload, key=lambda row: row["SE"])
            value = float(latest["casos_est"] if latest.get("casos_est") is not None else latest["casos"])
            week_start = geo_utils.parse_iso8601_utc(latest["data_iniSE"], assume_utc_if_naive=True)
        except (KeyError, TypeError, ValueError):
            return self._error("resposta do InfoDengue não contém os campos esperados")

        label = f"{DISEASE_LABELS_PT[disease]}: {value:.1f} casos estimados (semana {latest['SE']})"
        if (now - week_start) < timedelta(weeks=PRELIMINARY_WINDOW_WEEKS):
            label += " — dado preliminar, sujeito a revisão"

        record = GeoRecord(
            id=f"infodengue:{municipality.ibge_code}:{disease}",
            lat=municipality.lat,
            lon=municipality.lon,
            value=value,
            label=label,
            observation_time=week_start,
            raw=latest,
        )
        return self._ok([record], observation_time=week_start)


def _epidemiological_week(date) -> tuple[int, int]:
    """Best-effort approximation of the epidemiological week using ISO
    calendar week numbering. Exact alignment with InfoDengue's own epi-week
    convention (which may differ at year boundaries) could not be verified
    live; since the fetch requests a multi-week window and simply uses
    whichever week is most recent in the response, a small boundary
    discrepancy here does not affect correctness materially."""
    iso_year, iso_week, _ = date.isocalendar()
    return iso_year, iso_week
