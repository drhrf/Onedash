from __future__ import annotations

import streamlit as st

from onedash import strings_pt_br as t
from onedash.datasources.base import AreaOfInterest, SourceStatus
from onedash.datasources.cached import fetch_layer
from onedash.freshness import FreshnessLevel, compute_freshness
from onedash.layer_registry import LAYERS, all_layer_ids, get_layer
from onedash.map_builder import build_figure

FRESHNESS_COLOR = {
    FreshnessLevel.FRESH: "green",
    FreshnessLevel.AGING: "orange",
    FreshnessLevel.STALE: "red",
    FreshnessLevel.UNKNOWN: "gray",
}

_LAYER_OPTIONS = all_layer_ids()
_LAYER_LABELS = {layer.layer_id: layer.label_pt for layer in LAYERS}


@st.fragment
def render_panel(panel_index: int, aoi: AreaOfInterest, disease: str) -> None:
    key_prefix = f"panel_{panel_index}"

    selected_layer_ids = st.multiselect(
        t.PANEL_LAYER_SELECT_LABEL,
        options=_LAYER_OPTIONS,
        format_func=lambda layer_id: _LAYER_LABELS[layer_id],
        key=f"{key_prefix}_layers",
    )

    results = {
        layer_id: fetch_layer(layer_id, aoi.lat, aoi.lon, aoi.radius_km, disease=disease)
        for layer_id in selected_layer_ids
    }

    build_result = build_figure(aoi.lat, aoi.lon, results)
    st.plotly_chart(build_result.figure, width="stretch", key=f"{key_prefix}_map")

    if not selected_layer_ids:
        st.info(t.PANEL_NO_LAYERS_SELECTED)

    for warning in build_result.warnings:
        st.warning(warning)

    _render_freshness_badges(selected_layer_ids, results)


def _render_freshness_badges(selected_layer_ids: list[str], results: dict) -> None:
    lines = []
    for layer_id in selected_layer_ids:
        result = results.get(layer_id)
        if result is None or result.status is not SourceStatus.OK:
            continue
        layer = get_layer(layer_id)
        fresh = compute_freshness(result.observation_time, profile=layer.source_cls.freshness_profile)
        color = FRESHNESS_COLOR[fresh.level]
        lines.append(f":{color}[●] **{layer.label_pt}**: {fresh.description}")
    if lines:
        st.caption("  \n".join(lines))
