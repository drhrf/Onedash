from __future__ import annotations

import streamlit as st

from onedash import config
from onedash import strings_pt_br as t
from onedash.datasources.base import AreaOfInterest
from onedash.datasources.open_meteo_geocoding import search_locations
from onedash.grid_layout import SUPPORTED_PANEL_COUNTS


def render_sidebar() -> tuple[AreaOfInterest, str, int]:
    st.sidebar.header(t.SIDEBAR_LOCATION_HEADER)

    if "aoi_lat" not in st.session_state:
        st.session_state.aoi_lat = config.DEFAULT_AOI_LAT
        st.session_state.aoi_lon = config.DEFAULT_AOI_LON
        st.session_state.aoi_label = config.DEFAULT_AOI_LABEL

    query = st.sidebar.text_input(
        t.SIDEBAR_LOCATION_SEARCH_LABEL, placeholder=t.SIDEBAR_LOCATION_SEARCH_PLACEHOLDER, key="location_query"
    )
    if st.sidebar.button(t.SIDEBAR_LOCATION_SEARCH_BUTTON, key="location_search_button") and query.strip():
        search_result = search_locations(query)
        if not search_result.ok:
            st.sidebar.error(t.SIDEBAR_LOCATION_SEARCH_ERROR)
        elif not search_result.matches:
            st.sidebar.warning(t.SIDEBAR_LOCATION_NO_RESULTS)
        else:
            match = search_result.matches[0]
            st.session_state.aoi_lat = match.lat
            st.session_state.aoi_lon = match.lon
            st.session_state.aoi_label = match.display_label

    st.sidebar.caption(f"{t.SIDEBAR_CURRENT_LOCATION_PREFIX}: {st.session_state.aoi_label}")

    radius_km = st.sidebar.slider(
        t.SIDEBAR_RADIUS_LABEL,
        min_value=5.0,
        max_value=50.0,
        value=config.DEFAULT_AOI_RADIUS_KM,
        step=5.0,
        key="radius_km",
    )

    disease_id = st.sidebar.selectbox(
        t.SIDEBAR_DISEASE_LABEL,
        options=list(t.DISEASE_OPTIONS_PT),
        format_func=lambda key: t.DISEASE_OPTIONS_PT[key],
        key="disease_id",
    )

    panel_count = st.sidebar.select_slider(
        t.SIDEBAR_PANEL_COUNT_LABEL,
        options=SUPPORTED_PANEL_COUNTS,
        value=SUPPORTED_PANEL_COUNTS[0],
        key="panel_count",
    )

    aoi = AreaOfInterest(
        lat=st.session_state.aoi_lat,
        lon=st.session_state.aoi_lon,
        radius_km=radius_km,
        label=st.session_state.aoi_label,
    )
    return aoi, disease_id, panel_count
