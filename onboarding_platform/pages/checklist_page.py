"""
pages/checklist_page.py — View and interact with the onboarding checklist.
"""
from __future__ import annotations

import streamlit as st

from onboarding_platform.exceptions import ChecklistNotFoundError, ItemNotFoundError
from onboarding_platform.services.checklist_service import ChecklistService


def render(checklist_service: ChecklistService) -> None:
    st.header("✅ Onboarding Checklist")

    try:
        items = checklist_service.get_checklist()
    except ChecklistNotFoundError:
        st.info(
            "No checklist yet. Create your developer profile first "
            "and the checklist will be generated automatically."
        )
        return

    progress = checklist_service.get_progress()
    total = progress["total"]
    complete = progress["complete"]
    percent = progress["percent"]

    # Progress bar
    st.progress(int(percent) / 100, text=f"**{complete} / {total}** tasks complete ({percent}%)")
    st.divider()

    # Group by category
    categories: dict[str, list] = {}
    for item in items:
        categories.setdefault(item.category, []).append(item)

    for category, cat_items in categories.items():
        cat_complete = sum(1 for i in cat_items if i.is_complete)
        st.subheader(f"📂 {category}  ({cat_complete}/{len(cat_items)})")

        for item in cat_items:
            col_check, col_text = st.columns([0.08, 0.92])
            with col_check:
                checked = st.checkbox(
                    label="done",
                    value=item.is_complete,
                    key=f"chk_{item.item_id}",
                    label_visibility="collapsed",
                )
            with col_text:
                if item.is_complete:
                    st.markdown(f"~~**{item.title}**~~")
                else:
                    st.markdown(f"**{item.title}**")
                if item.description:
                    st.caption(item.description)

            # Detect toggle
            if checked != item.is_complete:
                try:
                    if checked:
                        checklist_service.mark_complete(item.item_id)
                    else:
                        checklist_service.mark_incomplete(item.item_id)
                    st.rerun()
                except (ChecklistNotFoundError, ItemNotFoundError) as exc:
                    st.error(f"❌ {exc}")
