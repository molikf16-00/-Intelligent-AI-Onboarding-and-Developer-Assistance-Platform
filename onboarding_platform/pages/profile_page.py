"""
pages/profile_page.py — Create / view the developer profile.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from onboarding_platform import config
from onboarding_platform.exceptions import ProfileAlreadyExistsError, ValidationError
from onboarding_platform.services.checklist_service import ChecklistService
from onboarding_platform.services.profile_service import ProfileService


def render(profile_service: ProfileService, checklist_service: ChecklistService) -> None:
    st.header("👤 Developer Profile")

    profile = profile_service.load_profile()

    if profile:
        st.success(f"Profile loaded: **{profile.name}**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Role", profile.role)
            st.metric("Team", profile.team)
        with col2:
            st.metric("Start Date", profile.start_date.isoformat())
            days = (date.today() - profile.start_date).days
            st.metric("Days Since Start", max(days, 0))

        st.divider()
        if st.button("🗑️ Reset Session (delete profile)", type="secondary"):
            profile_service.delete_profile()
            st.success("Profile deleted. Refresh the page to start over.")
            st.rerun()
        return

    # --- Create profile form ---
    st.info("No profile found. Fill in the form below to get started.")
    with st.form("profile_form"):
        name = st.text_input("Full Name *", placeholder="e.g. Jane Smith")
        role = st.selectbox("Role *", options=config.ALLOWED_ROLES)
        team = st.selectbox("Team *", options=config.ALLOWED_TEAMS)
        start_date = st.date_input(
            "Start Date *",
            value=date.today(),
            min_value=date.today().replace(year=date.today().year - 1),
            max_value=date.today().replace(year=date.today().year + 1),
        )
        submitted = st.form_submit_button("Create Profile", type="primary")

    if submitted:
        try:
            profile = profile_service.create_profile(
                name=name, role=role, team=team, start_date=start_date
            )
            checklist_service.generate_checklist(profile)
            st.success(
                f"✅ Profile created for **{profile.name}**! "
                "Your onboarding checklist has been generated."
            )
            st.rerun()
        except (ValidationError, ProfileAlreadyExistsError) as exc:
            st.error(f"❌ {exc}")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
