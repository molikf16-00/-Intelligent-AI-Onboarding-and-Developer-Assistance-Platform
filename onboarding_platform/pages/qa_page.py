"""
pages/qa_page.py — Ask questions about the codebase and view Q&A history.
"""
from __future__ import annotations

import streamlit as st

from onboarding_platform.exceptions import (
    AIServiceError,
    KnowledgeSourceNotReadyError,
    ValidationError,
)
from onboarding_platform.services.qa_service import QAService


def render(qa_service: QAService) -> None:
    st.header("💬 Ask the Codebase")

    # --- Question form ---
    with st.form("qa_form", clear_on_submit=True):
        question = st.text_area(
            "Ask a question about the codebase:",
            placeholder="e.g. How does authentication work in this project?",
            height=100,
        )
        submitted = st.form_submit_button("Ask", type="primary")

    if submitted:
        if not question.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner("Searching codebase and generating answer…"):
                try:
                    entry = qa_service.ask(question)
                    _render_entry(entry, show_resolve=False)
                    if entry.is_flagged:
                        st.warning(
                            "⚠️ This answer was **flagged for human follow-up** because "
                            "no highly relevant code was found. A team lead will review it."
                        )
                except KnowledgeSourceNotReadyError:
                    st.error(
                        "❌ No knowledge source is loaded yet. "
                        "Go to **Knowledge Source** and index a folder first."
                    )
                except ValidationError as exc:
                    st.error(f"❌ {exc}")
                except AIServiceError as exc:
                    st.error(f"❌ AI Error: {exc}")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")

    st.divider()

    # --- History ---
    st.subheader("📜 Q&A History")
    history = qa_service.get_history()
    if not history:
        st.info("No questions asked yet. Use the form above to ask your first question.")
        return

    for entry in history:
        with st.expander(
            f"{'🚩 ' if entry.is_flagged else ''}Q: {entry.question[:80]}…"
            if len(entry.question) > 80
            else f"{'🚩 ' if entry.is_flagged else ''}Q: {entry.question}",
            expanded=False,
        ):
            _render_entry(entry, show_resolve=False)


def _render_entry(entry, show_resolve: bool = False) -> None:  # type: ignore[no-untyped-def]
    st.markdown(f"**Question:** {entry.question}")
    st.markdown(f"**Answer:**\n\n{entry.answer}")
    col1, col2 = st.columns(2)
    with col1:
        conf_pct = f"{entry.confidence * 100:.0f}%"
        color = "green" if entry.confidence >= 0.5 else ("orange" if entry.confidence >= 0.25 else "red")
        st.markdown(f"**Confidence:** :{color}[{conf_pct}]")
    with col2:
        st.markdown(f"**Asked:** {entry.asked_at.strftime('%Y-%m-%d %H:%M')}")
    if entry.is_flagged:
        status = "✅ Resolved" if entry.is_resolved else "🚩 Flagged for review"
        st.markdown(f"**Status:** {status}")
    if entry.source_chunks:
        with st.expander("View retrieved snippets"):
            for chunk in entry.source_chunks:
                st.code(chunk, language="text")
