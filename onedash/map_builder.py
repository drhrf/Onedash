from __future__ import annotations

from dataclasses import dataclass, field

import plotly.graph_objects as go

from onedash.datasources.base import FetchResult, SourceStatus
from onedash.layer_registry import get_layer

DEFAULT_ZOOM = 10
DEFAULT_HEIGHT_PX = 520
MAP_STYLE = "open-street-map"
MARKER_SIZE = 14


@dataclass(frozen=True)
class FigureBuildResult:
    figure: go.Figure
    warnings: list[str] = field(default_factory=list)


def build_figure(
    center_lat: float,
    center_lon: float,
    results: dict[str, FetchResult],
    zoom: float = DEFAULT_ZOOM,
    height: int = DEFAULT_HEIGHT_PX,
) -> FigureBuildResult:
    """results maps layer_id -> FetchResult for whichever layers are
    currently selected on this panel. Never raises: bad/missing data for one
    layer becomes a warning message, not a broken panel — an empty
    `results` dict is valid and yields a base-map-only figure."""
    fig = go.Figure()
    warnings: list[str] = []

    for layer_id, result in results.items():
        try:
            layer = get_layer(layer_id)
        except KeyError:
            warnings.append(f"camada desconhecida: {layer_id}")
            continue

        if result.status is SourceStatus.ERROR:
            warnings.append(f"{layer.label_pt}: {result.error_message or 'erro ao buscar dados'}")
            continue
        if result.status is SourceStatus.UNSUPPORTED_LOCATION:
            warnings.append(f"{layer.label_pt}: {result.error_message or 'não disponível para este local'}")
            continue
        if result.status is SourceStatus.EMPTY:
            warnings.append(f"{layer.label_pt}: nenhum dado encontrado nesta área")
            continue

        points = [r for r in result.records if r.lat is not None and r.lon is not None]
        if not points:
            warnings.append(f"{layer.label_pt}: nenhum dado com coordenadas válidas")
            continue

        fig.add_trace(
            go.Scattermap(
                lat=[p.lat for p in points],
                lon=[p.lon for p in points],
                mode="markers",
                marker=dict(size=MARKER_SIZE, color=layer.color),
                text=[p.label for p in points],
                hoverinfo="text",
                name=layer.label_pt,
            )
        )

    if not fig.data:
        # Plotly only renders the `map` subplot (tiles, pan/zoom) when the
        # figure has at least one map-type trace — a layout.map config with
        # zero traces silently falls back to a generic Cartesian axes plot
        # instead of a map. An invisible empty trace keeps the map view (and
        # the "select a layer" info message that accompanies it) correct
        # even when no data layer is active.
        fig.add_trace(go.Scattermap(lat=[], lon=[], mode="markers", showlegend=False))

    fig.update_layout(
        map=dict(style=MAP_STYLE, center=dict(lat=center_lat, lon=center_lon), zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        height=height,
    )
    return FigureBuildResult(figure=fig, warnings=warnings)
