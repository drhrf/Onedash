import streamlit as st

from onedash import strings_pt_br as t
from onedash.ui.panel import render_panel
from onedash.ui.sidebar import render_sidebar

st.set_page_config(page_title=t.APP_TITLE, layout="wide")
st.title(t.APP_TITLE)

aoi, disease = render_sidebar()
render_panel(0, aoi, disease)
