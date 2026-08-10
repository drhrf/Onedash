from __future__ import annotations

import streamlit as st

from onedash import config
from onedash.datasources.base import AreaOfInterest, FetchResult
from onedash.layer_registry import get_layer


@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner=False)
def fetch_layer(layer_id: str, lat: float, lon: float, radius_km: float, disease: str = "dengue") -> FetchResult:
    """Cached fetch adapter — the only module in datasources/ allowed to
    import streamlit. Takes only hashable primitives (never a DataSource
    instance or requests.Session, which st.cache_data can't hash) and looks
    up/constructs everything else inside the function body."""
    layer = get_layer(layer_id)
    source = layer.source_cls()
    aoi = AreaOfInterest(lat=lat, lon=lon, radius_km=radius_km)
    params = {"disease": disease} if layer_id == "infodengue" else {}
    return source.fetch(aoi, params)
