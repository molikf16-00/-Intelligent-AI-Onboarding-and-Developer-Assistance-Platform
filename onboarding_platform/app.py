"""
app.py — Streamlit entry point for the Intelligent AI Onboarding Platform.

Run with:
    streamlit run onboarding_platform/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root (parent of the onboarding_platform package) is on sys.path
# regardless of the working directory Streamlit is launched from.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from onboarding_platform.services.checklist_service import ChecklistService
from onboarding_platform.services.dashboard_service import DashboardService
from onboarding_platform.services.knowledge_service import KnowledgeService
from onboarding_platform.services.profile_service import ProfileService
from onboarding_platform.services.qa_service import QAService
from onboarding_platform.pages import (
    checklist_page,
    dashboard_page,
    flagged_page,
    knowledge_page,
    profile_page,
    qa_page,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Onboarding Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Service wiring (created once per session via st.cache_resource)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_services() -> dict:
    profile_svc = ProfileService()
    knowledge_svc = KnowledgeService()
    checklist_svc = ChecklistService()
    qa_svc = QAService(knowledge_service=knowledge_svc)
    dashboard_svc = DashboardService(checklist_service=checklist_svc)

    # Restore persisted knowledge source metadata (index rebuilt on re-ingest)
    knowledge_svc.load_meta()

    return {
        "profile": profile_svc,
        "knowledge": knowledge_svc,
        "checklist": checklist_svc,
        "qa": qa_svc,
        "dashboard": dashboard_svc,
    }


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

PAGES = {
    "👤 Profile": "profile",
    "📁 Knowledge Source": "knowledge",
    "💬 Ask a Question": "qa",
    "✅ Checklist": "checklist",
    "📊 Dashboard": "dashboard",
    "🚩 Flagged Questions": "flagged",
}

services = get_services()

with st.sidebar:
    st.title("🚀 AI Onboarding")
    st.caption("Developer Assistance Platform")
    st.divider()

    profile_svc: ProfileService = services["profile"]
    profile = profile_svc.load_profile()

    if profile:
        st.success(f"👋 Hello, **{profile.name}**")
        st.caption(f"Role: {profile.role}  \nTeam: {profile.team}")
    else:
        st.warning("No profile yet. Create one first.")

    st.divider()
    selected_page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

# ---------------------------------------------------------------------------
# Render selected page
# ---------------------------------------------------------------------------

page_key = PAGES[selected_page]

if page_key == "profile":
    profile_page.render(
        profile_service=services["profile"],
        checklist_service=services["checklist"],
    )

elif page_key == "knowledge":
    if not profile:
        st.warning("⚠️ Please create your profile first.")
    else:
        knowledge_page.render(knowledge_service=services["knowledge"])

elif page_key == "qa":
    if not profile:
        st.warning("⚠️ Please create your profile first.")
    else:
        qa_page.render(qa_service=services["qa"])

elif page_key == "checklist":
    if not profile:
        st.warning("⚠️ Please create your profile first.")
    else:
        checklist_page.render(checklist_service=services["checklist"])

elif page_key == "dashboard":
    if not profile:
        st.warning("⚠️ Please create your profile first.")
    else:
        dashboard_page.render(
            dashboard_service=services["dashboard"],
            profile=profile,
        )

elif page_key == "flagged":
    if not profile:
        st.warning("⚠️ Please create your profile first.")
    else:
        flagged_page.render(qa_service=services["qa"])
