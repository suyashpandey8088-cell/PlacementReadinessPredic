"""Launch from the repository root with: streamlit run app.py."""
import streamlit as st
from src import ui
from src.config import ROOT

st.set_page_config(page_title="Path2Placement · Prepare with purpose", page_icon=str(ROOT / "assets/icon.svg"), layout="wide", initial_sidebar_state="auto")
ui.initialize()
ui.styles()
pages = {
    "home": st.Page(ui.home, title="Overview", icon=":material/space_dashboard:", default=True),
    "assess": st.Page(ui.assessment, title="Assess my readiness", icon=":material/checklist:", url_path="assessment"),
    "results": st.Page(ui.results, title="My results", icon=":material/bar_chart:", url_path="results"),
    "progress": st.Page(ui.progress, title="My progress", icon=":material/trending_up:", url_path="progress"),
    "model": st.Page(ui.model_insights, title="Model insights", icon=":material/science:", url_path="model"),
    "about": st.Page(ui.about, title="About the project", icon=":material/info:", url_path="about"),
}
st.session_state["pages"] = pages
st.logo(str(ROOT / "assets/wordmark.svg"), size="large", icon_image=str(ROOT / "assets/icon.svg"))
nav = st.navigation({"Your workspace": list(pages.values())[:4], "Behind the assessment": list(pages.values())[4:]})
with st.sidebar:
    ui.workspace_controls()
    st.markdown('<div class="sidebar-note">A little clarity.<br>A practical next step.<br><strong>Your preparation, at your pace.</strong></div>', unsafe_allow_html=True)
nav.run()
