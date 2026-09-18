"""
pages/flagged_page.py — View and resolve flagged Q&A entries.
"""
from __future__ import annotations

import streamlit as st

from onboarding_platform.services.qa_service import QAService


def render(qa_service: QAService) -> None:
    st.header("🚩 Flagged Questions")
    st.write(
        "These questions were flagged because the AI couldn't find a confident answer "
        "in the codebase. A team lead or buddy should review and follow up."
    )

    flagged = qa_service.get_flagged()

    if not flagged:
        st.success("✅ No outstanding flagged questions. Great job!")
        return

    st.info(f"**{len(flagged)}** question(s) need human review.")

    for entry in flagged:
        with st.expander(
            f"🚩 {entry.question[:80]}…" if len(entry.question) > 80 else f"🚩 {entry.question}"
        ):
            st.markdown(f"**Question:** {entry.question}")
            st.markdown(f"**AI Response:**\n\n{entry.answer}")
            conf_pct = f"{entry.confidence * 100:.0f}%"
            st.markdown(f"**Confidence:** {conf_pct}  ·  **Asked:** {entry.asked_at.strftime('%Y-%m-%d %H:%M')}")

            if st.button("✅ Mark as Resolved", key=f"resolve_{entry.entry_id}"):
                try:
                    qa_service.resolve_flag(entry.entry_id)
                    st.success("Marked as resolved.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error: {exc}")
