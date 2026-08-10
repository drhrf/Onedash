from __future__ import annotations

import streamlit as st

from onedash import strings_pt_br as t
from onedash.datasources.base import AreaOfInterest, SourceStatus
from onedash.datasources.cached import fetch_layer
from onedash.grid_layout import map_height_px
from onedash.layer_registry import LAYERS, all_layer_ids, get_layer
from onedash.map_builder import build_figure
from onedash.summaries import freshness_line

_LAYER_OPTIONS = all_layer_ids()
_LAYER_LABELS = {layer.layer_id: layer.label_pt for layer in LAYERS}


@st.fragment
def render_panel(panel_index: int, aoi: AreaOfInterest, disease: str, panel_count: int = 1) -> None:
    key_prefix = f"panel_{panel_index}"

    selected_layer_ids = st.multiselect(
        t.PANEL_LAYER_SELECT_LABEL,
        options=_LAYER_OPTIONS,
        format_func=lambda layer_id: _LAYER_LABELS[layer_id],
        placeholder=t.PANEL_LAYER_SELECT_PLACEHOLDER,
        key=f"{key_prefix}_layers",
    )

    results = {
        layer_id: fetch_layer(layer_id, aoi.lat, aoi.lon, aoi.radius_km, disease=disease)
        for layer_id in selected_layer_ids
    }

    build_result = build_figure(aoi.lat, aoi.lon, results, height=map_height_px(panel_count))
    st.plotly_chart(build_result.figure, width="stretch", key=f"{key_prefix}_map")

    if not selected_layer_ids:
        st.info(t.PANEL_NO_LAYERS_SELECTED)

    for warning in build_result.warnings:
        st.warning(warning)

    _render_freshness_badges(selected_layer_ids, results)


def _render_freshness_badges(selected_layer_ids: list[str], results: dict) -> None:
    lines = [
        freshness_line(get_layer(layer_id), results[layer_id])
        for layer_id in selected_layer_ids
        if layer_id in results and results[layer_id].status is SourceStatus.OK
    ]
    if lines:
        st.caption("  \n".join(lines))
