"""
KnowledgeService — indexes a local codebase folder (or uploaded file bytes)
and provides keyword-based snippet retrieval.

Design:
  * The "index" is an in-memory list of (file_path, chunk_text) tuples.
  * Retrieval scores each chunk by counting how many query tokens appear in it.
  * No external vector DB needed — suitable for small codebases.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from onboarding_platform import config
from onboarding_platform.exceptions import (
    InvalidFileTypeError,
    KnowledgeSourceNotReadyError,
    PathNotFoundError,
)
from onboarding_platform.models import KnowledgeSource, SourceType
from onboarding_platform.repositories import KnowledgeRepository


# A single indexable chunk of text with its source file path
class _Chunk:
    __slots__ = ("file_path", "text")

    def __init__(self, file_path: str, text: str) -> None:
        self.file_path = file_path
        self.text = text


class KnowledgeService:
    """Ingests files and retrieves relevant snippets for Q&A."""

    def __init__(self, repo: Optional[KnowledgeRepository] = None) -> None:
        self._repo = repo or KnowledgeRepository()
        self._chunks: list[_Chunk] = []
        self._source: Optional[KnowledgeSource] = None

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_directory(self, path: str) -> KnowledgeSource:
        """
        Walk *path* recursively, read supported files, build the in-memory index.
        Returns a KnowledgeSource with metadata.
        Raises PathNotFoundError if the directory does not exist.
        """
        dir_path = Path(path)
        if not dir_path.exists() or not dir_path.is_dir():
            raise PathNotFoundError(f"Directory not found: {path}")

        chunks: list[_Chunk] = []
        for file_path in sorted(dir_path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in config.SUPPORTED_EXTENSIONS:
                if file_path.stat().st_size > config.MAX_FILE_BYTES:
                    continue  # skip oversized files
                text = self._read_file_safe(file_path)
                if text:
                    chunks.extend(self._split_into_chunks(str(file_path), text))

        self._chunks = chunks
        source = KnowledgeSource(
            path=str(dir_path.resolve()),
            source_type=SourceType.LOCAL_DIR,
            indexed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            file_count=len({c.file_path for c in chunks}),
        )
        self._source = source
        self._repo.save(source)
        return source

    def ingest_uploaded_files(self, files: list[tuple[str, bytes]]) -> KnowledgeSource:
        """
        Accept a list of (filename, content_bytes) pairs and index them.
        Raises InvalidFileTypeError if any file has an unsupported extension.
        """
        chunks: list[_Chunk] = []
        for filename, content_bytes in files:
            ext = Path(filename).suffix.lower()
            if ext not in config.SUPPORTED_EXTENSIONS:
                raise InvalidFileTypeError(
                    f"File '{filename}' has unsupported extension '{ext}'. "
                    f"Supported: {', '.join(config.SUPPORTED_EXTENSIONS)}"
                )
            if len(content_bytes) > config.MAX_FILE_BYTES:
                continue  # skip oversized
            try:
                text = content_bytes.decode("utf-8", errors="replace")
            except Exception:
                continue
            if text.strip():
                chunks.extend(self._split_into_chunks(filename, text))

        self._chunks = chunks
        source = KnowledgeSource(
            path="(uploaded files)",
            source_type=SourceType.UPLOADED_FILE,
            indexed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            file_count=len({c.file_path for c in chunks}),
        )
        self._source = source
        self._repo.save(source)
        return source

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5) -> tuple[list[str], float]:
        """
        Return (list_of_snippets, confidence_score).

        confidence_score is in [0.0, 1.0].  It is the normalised keyword-match
        score of the best chunk:
          * 0.0 → no chunks matched at all
          * 1.0 → every query token matched the best chunk

        Raises KnowledgeSourceNotReadyError if nothing has been indexed yet.
        """
        if not self._chunks:
            # Try restoring metadata — the index itself is in-memory only.
            if self._repo.exists():
                raise KnowledgeSourceNotReadyError(
                    "Knowledge source metadata found but the index is not loaded. "
                    "Please re-ingest the knowledge source."
                )
            raise KnowledgeSourceNotReadyError(
                "No knowledge source has been indexed yet."
            )

        tokens = self._tokenise(query)
        if not tokens:
            return [], 0.0

        scored: list[tuple[float, _Chunk]] = []
        for chunk in self._chunks:
            score = self._score_chunk(chunk.text.lower(), tokens)
            if score > 0:
                scored.append((score, chunk))

        if not scored:
            return [], 0.0

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score = scored[0][0]
        confidence = min(best_score / len(tokens), 1.0)

        snippets = []
        total_chars = 0
        for score, chunk in scored[:top_k]:
            snippet = f"# {chunk.file_path}\n{chunk.text[:800]}"
            if total_chars + len(snippet) > config.MAX_SNIPPET_CHARS:
                break
            snippets.append(snippet)
            total_chars += len(snippet)

        return snippets, confidence

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def is_index_ready(self) -> bool:
        return bool(self._chunks)

    def get_current_source(self) -> Optional[KnowledgeSource]:
        return self._source

    def load_meta(self) -> Optional[KnowledgeSource]:
        """Load persisted metadata (index itself must be rebuilt manually)."""
        self._source = self._repo.load()
        return self._source

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_file_safe(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    @staticmethod
    def _split_into_chunks(file_path: str, text: str, chunk_size: int = 400) -> list[_Chunk]:
        """
        Split *text* into overlapping chunks of ~*chunk_size* characters.
        Overlap helps avoid cutting a relevant snippet in half.
        """
        lines = text.splitlines(keepends=True)
        chunks: list[_Chunk] = []
        current: list[str] = []
        current_len = 0

        for line in lines:
            current.append(line)
            current_len += len(line)
            if current_len >= chunk_size:
                chunks.append(_Chunk(file_path, "".join(current)))
                # 25% overlap: keep last quarter of lines
                overlap_start = max(0, len(current) - max(1, len(current) // 4))
                current = current[overlap_start:]
                current_len = sum(len(l) for l in current)

        if current:
            chunks.append(_Chunk(file_path, "".join(current)))

        return chunks

    @staticmethod
    def _tokenise(text: str) -> list[str]:
        """Lower-case word tokens, filtered to length >= 3."""
        return [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) >= 3]

    @staticmethod
    def _score_chunk(chunk_lower: str, tokens: list[str]) -> float:
        """Count how many unique query tokens appear in the chunk."""
        return sum(1.0 for t in set(tokens) if t in chunk_lower)
