"""
pages/dashboard_page.py — Summary / progress overview.
"""
from __future__ import annotations

import streamlit as st

from onboarding_platform.models import DeveloperProfile
from onboarding_platform.services.dashboard_service import DashboardService


def render(dashboard_service: DashboardService, profile: DeveloperProfile) -> None:
    st.header("📊 Onboarding Dashboard")

    summary = dashboard_service.get_summary(profile)
    p = summary["profile"]
    cl = summary["checklist"]
    qa = summary["qa"]

    # --- Profile summary ---
    st.subheader("👤 Profile")
    cols = st.columns(4)
    cols[0].metric("Name", p["name"])
    cols[1].metric("Role", p["role"])
    cols[2].metric("Team", p["team"])
    days = p["days_since_start"]
    cols[3].metric("Days Since Start", max(days, 0))

    st.divider()

    # --- Checklist progress ---
    st.subheader("✅ Checklist Progress")
    if cl["total"] == 0:
        st.info("No checklist items found.")
    else:
        percent = cl["percent"]
        st.progress(int(percent) / 100, text=f"{cl['complete']} / {cl['total']} tasks complete ({percent}%)")

        if cl["by_category"]:
            st.write("**By Category:**")
            cat_cols = st.columns(min(len(cl["by_category"]), 4))
            for idx, (cat, stats) in enumerate(cl["by_category"].items()):
                col_idx = idx % 4
                cat_pct = (
                    round(stats["complete"] / stats["total"] * 100, 0)
                    if stats["total"] > 0 else 0
                )
                cat_cols[col_idx].metric(cat, f"{stats['complete']}/{stats['total']}", f"{cat_pct}%")

    st.divider()

    # --- Q&A summary ---
    st.subheader("💬 Q&A Activity")
    qa_cols = st.columns(3)
    qa_cols[0].metric("Total Questions", qa["total_questions"])
    qa_cols[1].metric("Flagged", qa["flagged_count"])
    qa_cols[2].metric("Resolved", qa["resolved_count"])

    if qa["flagged_count"] > qa["resolved_count"]:
        pending = qa["flagged_count"] - qa["resolved_count"]
        st.warning(
            f"⚠️ **{pending}** flagged question(s) are waiting for human review. "
            "Check the **Flagged Questions** page."
        )
    elif qa["total_questions"] > 0:
        st.success("✅ All flagged questions have been resolved!")
