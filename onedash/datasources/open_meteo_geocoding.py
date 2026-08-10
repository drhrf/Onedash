from __future__ import annotations

from dataclasses import dataclass, field

import requests

BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"


@dataclass(frozen=True)
class GeocodeMatch:
    name: str
    lat: float
    lon: float
    country: str | None = None
    admin1: str | None = None

    @property
    def display_label(self) -> str:
        parts = [self.name]
        if self.admin1:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)


@dataclass(frozen=True)
class GeocodeSearchResult:
    query: str
    matches: list[GeocodeMatch] = field(default_factory=list)
    error_message: str | None = None

    @property
    def ok(self) -> bool:
        return self.error_message is None


def search_locations(
    query: str,
    session: requests.Session | None = None,
    timeout: float = 10.0,
    limit: int = 5,
) -> GeocodeSearchResult:
    query = query.strip()
    if not query:
        return GeocodeSearchResult(query=query, matches=[])

    session = session or requests.Session()
    params = {"name": query, "count": limit, "language": "pt", "format": "json"}
    try:
        response = session.get(BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return GeocodeSearchResult(query=query, error_message="tempo de resposta esgotado na busca por local")
    except requests.exceptions.ConnectionError:
        return GeocodeSearchResult(query=query, error_message="falha de conexão na busca por local")
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "desconhecido"
        return GeocodeSearchResult(query=query, error_message=f"erro HTTP {status_code} na busca por local")
    except requests.exceptions.RequestException as exc:
        return GeocodeSearchResult(query=query, error_message=f"erro na busca por local: {exc}")

    try:
        payload = response.json()
    except ValueError:
        return GeocodeSearchResult(query=query, error_message="resposta inválida (JSON malformado) na busca por local")

    raw_results = payload.get("results") or []
    matches = []
    for item in raw_results:
        try:
            matches.append(
                GeocodeMatch(
                    name=str(item["name"]),
                    lat=float(item["latitude"]),
                    lon=float(item["longitude"]),
                    country=item.get("country"),
                    admin1=item.get("admin1"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue  # skip a malformed individual result rather than failing the whole search

    return GeocodeSearchResult(query=query, matches=matches)
