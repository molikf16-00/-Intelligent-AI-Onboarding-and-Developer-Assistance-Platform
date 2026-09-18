"""
Tests for KnowledgeService.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from onboarding_platform.exceptions import (
    InvalidFileTypeError,
    KnowledgeSourceNotReadyError,
    PathNotFoundError,
)
from onboarding_platform.models import SourceType
from onboarding_platform.repositories import KnowledgeRepository
from onboarding_platform.services.knowledge_service import KnowledgeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service(tmp_path: Path) -> KnowledgeService:
    repo = KnowledgeRepository(path=tmp_path / "knowledge_meta.json")
    return KnowledgeService(repo=repo)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a tiny fake codebase in a temp directory."""
    (tmp_path / "main.py").write_text(
        "def authenticate(user, password):\n    return user == 'admin' and password == 'secret'\n"
    )
    (tmp_path / "README.md").write_text(
        "# My Project\nThis project handles user authentication.\n"
    )
    (tmp_path / "utils.py").write_text(
        "def hash_password(pw):\n    import hashlib\n    return hashlib.sha256(pw.encode()).hexdigest()\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# ingest_directory
# ---------------------------------------------------------------------------

def test_ingest_directory_success(service: KnowledgeService, sample_repo: Path) -> None:
    source = service.ingest_directory(str(sample_repo))
    assert source.file_count >= 3
    assert source.source_type == SourceType.LOCAL_DIR
    assert service.is_index_ready()


def test_ingest_directory_not_found(service: KnowledgeService, tmp_path: Path) -> None:
    with pytest.raises(PathNotFoundError):
        service.ingest_directory(str(tmp_path / "nonexistent"))


def test_ingest_empty_directory(service: KnowledgeService, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    source = service.ingest_directory(str(empty))
    assert source.file_count == 0


# ---------------------------------------------------------------------------
# ingest_uploaded_files
# ---------------------------------------------------------------------------

def test_ingest_uploaded_files_success(service: KnowledgeService) -> None:
    files = [
        ("auth.py", b"def login(user): return True"),
        ("notes.md", b"# Notes\nSome documentation here."),
    ]
    source = service.ingest_uploaded_files(files)
    assert source.file_count == 2
    assert source.source_type == SourceType.UPLOADED_FILE


def test_ingest_uploaded_files_invalid_type(service: KnowledgeService) -> None:
    files = [("image.png", b"\x89PNG\r\n")]
    with pytest.raises(InvalidFileTypeError):
        service.ingest_uploaded_files(files)


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------

def test_retrieve_no_index_raises(service: KnowledgeService) -> None:
    with pytest.raises(KnowledgeSourceNotReadyError):
        service.retrieve("authentication")


def test_retrieve_finds_relevant_chunk(service: KnowledgeService, sample_repo: Path) -> None:
    service.ingest_directory(str(sample_repo))
    snippets, confidence = service.retrieve("authenticate user password")
    assert len(snippets) > 0
    assert confidence > 0.0


def test_retrieve_no_match_returns_zero_confidence(
    service: KnowledgeService, sample_repo: Path
) -> None:
    service.ingest_directory(str(sample_repo))
    snippets, confidence = service.retrieve("xyz completely irrelevant zzzz")
    assert confidence == 0.0
    assert snippets == []


def test_retrieve_confidence_capped_at_one(
    service: KnowledgeService, sample_repo: Path
) -> None:
    service.ingest_directory(str(sample_repo))
    _, confidence = service.retrieve("authenticate user password login secret")
    assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

def test_tokenise_filters_short_words() -> None:
    # Tokeniser removes words with fewer than 3 characters; 3-char words are kept.
    tokens = KnowledgeService._tokenise("a is to the function")
    assert "a" not in tokens      # 1 char — filtered
    assert "is" not in tokens     # 2 chars — filtered
    assert "to" not in tokens     # 2 chars — filtered
    assert "the" in tokens        # exactly 3 chars — kept (filter is < 3, not <= 3)
    assert "function" in tokens   # long word — kept


def test_score_chunk_counts_unique_tokens() -> None:
    score = KnowledgeService._score_chunk("authenticate user password", ["authenticate", "user", "unknown"])
    assert score == 2.0  # "authenticate" and "user" match; "unknown" does not
