from __future__ import annotations

from dataclasses import dataclass

from onedash import geo_utils


@dataclass(frozen=True)
class Municipality:
    name: str
    ibge_code: int  # 7-digit IBGE code; InfoDengue's `geocode` param requires the exact value
    lat: float
    lon: float


# Região dos Lagos, RJ. These codes were cross-referenced via web search
# against multiple independent tertiary sources (a SPED/fiscal municipality
# table, Wikidata) after the first hardcoded attempt at this table (from
# memory) turned out to have the wrong code for Cabo Frio — that mistake
# was only caught because the corrected value is directly corroborated by
# an IBGE geoftp.ibge.gov.br filename ("3300704_MM.pdf"). This sandbox's
# network policy blocks a live hit against IBGE's own API
# (servicodados.ibge.gov.br/api/v1/localidades/municipios) to fully confirm
# all seven — that direct confirmation is still recommended before treating
# this table as authoritative.
REGIAO_DOS_LAGOS: tuple[Municipality, ...] = (
    Municipality("Cabo Frio", 3300704, -22.8894, -42.0286),
    Municipality("Armação dos Búzios", 3300233, -22.7469, -41.8817),
    Municipality("Arraial do Cabo", 3300258, -22.9661, -42.0278),
    Municipality("São Pedro da Aldeia", 3305505, -22.8386, -42.1028),
    Municipality("Iguaba Grande", 3301876, -22.8425, -42.2286),
    Municipality("Araruama", 3300209, -22.8722, -42.3436),
    Municipality("Saquarema", 3305554, -22.9200, -42.5100),
)

DEFAULT_MATCH_RADIUS_KM = 40.0


def find_nearest(lat: float, lon: float, max_distance_km: float = DEFAULT_MATCH_RADIUS_KM) -> Municipality | None:
    """Returns the closest known municipality if it's within max_distance_km,
    else None. Used to decide whether Brazil/region-specific sources (like
    InfoDengue) apply to a given AreaOfInterest."""
    best: Municipality | None = None
    best_distance = float("inf")
    for municipality in REGIAO_DOS_LAGOS:
        distance = geo_utils.haversine_km(lat, lon, municipality.lat, municipality.lon)
        if distance < best_distance:
            best, best_distance = municipality, distance
    if best is not None and best_distance <= max_distance_km:
        return best
    return None
