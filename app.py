import streamlit as st

from onedash import strings_pt_br as t
from onedash.grid_layout import compute_rows
from onedash.ui.panel import render_panel
from onedash.ui.sidebar import render_sidebar

st.set_page_config(page_title=t.APP_TITLE, layout="wide")
st.title(t.APP_TITLE)

aoi, disease, panel_count = render_sidebar()

for row in compute_rows(panel_count):
    columns = st.columns(len(row))
    for column, panel_index in zip(columns, row):
        with column:
            render_panel(panel_index, aoi, disease)
