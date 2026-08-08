import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Painel de Saúde e Clima — Cabo Frio", layout="wide")

st.title("Painel de Saúde e Clima — Região dos Lagos")

CABO_FRIO_LAT = -22.8894
CABO_FRIO_LON = -42.0286

fig = go.Figure(
    go.Scattermap(
        lat=[CABO_FRIO_LAT],
        lon=[CABO_FRIO_LON],
        mode="markers",
        marker=dict(size=14, color="#2563eb"),
        text=["Cabo Frio"],
        hoverinfo="text",
    )
)
fig.update_layout(
    map=dict(
        style="open-street-map",
        center=dict(lat=CABO_FRIO_LAT, lon=CABO_FRIO_LON),
        zoom=9,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=600,
)

st.plotly_chart(fig, use_container_width=True)
