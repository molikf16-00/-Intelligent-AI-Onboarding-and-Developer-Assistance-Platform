"""
pages/knowledge_page.py — Index a local codebase folder or upload files.
"""
from __future__ import annotations

import streamlit as st

from onboarding_platform.exceptions import InvalidFileTypeError, PathNotFoundError
from onboarding_platform.services.knowledge_service import KnowledgeService


def render(knowledge_service: KnowledgeService) -> None:
    st.header("📁 Knowledge Source")
    st.write(
        "Point the app at your codebase so the AI can answer questions about it. "
        "You can either provide a local folder path **or** upload individual files."
    )

    current = knowledge_service.get_current_source()
    if current:
        st.success(
            f"✅ **Indexed:** `{current.path}`  \n"
            f"Files indexed: **{current.file_count}** · "
            f"Last updated: {current.indexed_at.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        st.divider()

    tab_dir, tab_upload = st.tabs(["📂 Local Directory", "📤 Upload Files"])

    # --- Local directory ---
    with tab_dir:
        folder_path = st.text_input(
            "Enter the absolute path to your codebase folder:",
            placeholder="/home/user/my-project",
        )
        if st.button("Index Directory", type="primary"):
            if not folder_path.strip():
                st.error("Please enter a folder path.")
            else:
                with st.spinner("Indexing files…"):
                    try:
                        source = knowledge_service.ingest_directory(folder_path.strip())
                        st.success(
                            f"✅ Indexed **{source.file_count}** file(s) from `{source.path}`."
                        )
                        if source.file_count == 0:
                            st.warning(
                                "No supported files were found. Make sure the folder contains "
                                ".py, .md, .txt, .js, .ts, .json, .yaml, or .rst files."
                            )
                    except PathNotFoundError as exc:
                        st.error(f"❌ {exc}")
                    except Exception as exc:
                        st.error(f"Unexpected error: {exc}")

    # --- File upload ---
    with tab_upload:
        uploaded = st.file_uploader(
            "Upload source files (multiple allowed):",
            accept_multiple_files=True,
            type=["py", "md", "txt", "js", "ts", "json", "yaml", "yml", "rst"],
        )
        if st.button("Index Uploaded Files", type="primary"):
            if not uploaded:
                st.error("Please upload at least one file.")
            else:
                files = [(f.name, f.read()) for f in uploaded]
                with st.spinner("Indexing uploaded files…"):
                    try:
                        source = knowledge_service.ingest_uploaded_files(files)
                        st.success(
                            f"✅ Indexed **{source.file_count}** uploaded file(s)."
                        )
                    except InvalidFileTypeError as exc:
                        st.error(f"❌ {exc}")
                    except Exception as exc:
                        st.error(f"Unexpected error: {exc}")
