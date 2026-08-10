from __future__ import annotations

from dataclasses import dataclass

from onedash.datasources.base import DataSource
from onedash.datasources.infodengue import InfoDengueSource
from onedash.datasources.open_meteo_air_quality import OpenMeteoAirQualitySource
from onedash.datasources.open_meteo_marine import OpenMeteoMarineSource
from onedash.datasources.open_meteo_weather import OpenMeteoWeatherSource
from onedash.datasources.overpass_health import OverpassHealthSource


@dataclass(frozen=True)
class LayerDefinition:
    label_pt: str
    source_cls: type[DataSource]
    color: str
    # Plural noun used when a layer returns many records and listing every
    # label would be useless ("128 estabelecimentos" beats 128 hospital names
    # in a caption). Single-record layers show their own label instead.
    record_noun_pt: str = "registros"

    @property
    def layer_id(self) -> str:
        return self.source_cls.source_id


LAYERS: tuple[LayerDefinition, ...] = (
    LayerDefinition("Clima atual", OpenMeteoWeatherSource, color="#f97316", record_noun_pt="medições"),
    LayerDefinition("Qualidade do ar", OpenMeteoAirQualitySource, color="#8b5cf6", record_noun_pt="medições"),
    LayerDefinition("Condições marítimas", OpenMeteoMarineSource, color="#0ea5e9", record_noun_pt="medições"),
    LayerDefinition(
        "Estabelecimentos de saúde", OverpassHealthSource, color="#ef4444", record_noun_pt="estabelecimentos"
    ),
    LayerDefinition("Vigilância de arboviroses", InfoDengueSource, color="#22c55e", record_noun_pt="municípios"),
)

_BY_ID = {layer.layer_id: layer for layer in LAYERS}


def get_layer(layer_id: str) -> LayerDefinition:
    return _BY_ID[layer_id]


def all_layer_ids() -> list[str]:
    return [layer.layer_id for layer in LAYERS]
