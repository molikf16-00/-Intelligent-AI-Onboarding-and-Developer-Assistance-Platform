"""
Tests for QAService.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from onboarding_platform.exceptions import AIServiceError, ValidationError
from onboarding_platform.models import QAEntry
from onboarding_platform.repositories import QARepository
from onboarding_platform.services.knowledge_service import KnowledgeService
from onboarding_platform.services.qa_service import QAService
from onboarding_platform import config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def knowledge_service_with_index(tmp_path: Path) -> KnowledgeService:
    """A KnowledgeService pre-loaded with a tiny in-memory index."""
    from onboarding_platform.repositories import KnowledgeRepository
    repo = KnowledgeRepository(path=tmp_path / "km.json")
    svc = KnowledgeService(repo=repo)
    svc.ingest_uploaded_files([
        ("auth.py", b"def authenticate(user, password):\n    return user == 'admin'\n"),
        ("utils.py", b"def hash_password(pw):\n    import hashlib\n    return hashlib.sha256(pw.encode()).hexdigest()\n"),
    ])
    return svc


@pytest.fixture
def qa_service(tmp_path: Path, knowledge_service_with_index: KnowledgeService) -> QAService:
    repo = QARepository(path=tmp_path / "qa.json")
    return QAService(knowledge_service=knowledge_service_with_index, repo=repo)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_ask_empty_question_raises(qa_service: QAService) -> None:
    with pytest.raises(ValidationError) as exc_info:
        qa_service.ask("")
    assert exc_info.value.field == "question"


def test_ask_too_short_raises(qa_service: QAService) -> None:
    with pytest.raises(ValidationError):
        qa_service.ask("Hi")


def test_ask_too_long_raises(qa_service: QAService) -> None:
    with pytest.raises(ValidationError):
        qa_service.ask("x" * 1001)


# ---------------------------------------------------------------------------
# Successful ask (no API key → fallback response)
# ---------------------------------------------------------------------------

def test_ask_no_api_key_returns_entry(qa_service: QAService) -> None:
    """Without an API key the service should return a demo response, not raise."""
    original_key = config.OPENAI_API_KEY
    config.OPENAI_API_KEY = ""  # ensure no key
    try:
        entry = qa_service.ask("How does authentication work?")
        assert isinstance(entry, QAEntry)
        assert entry.question == "How does authentication work?"
        assert len(entry.answer) > 0
    finally:
        config.OPENAI_API_KEY = original_key


def test_ask_with_matching_snippets_high_confidence(qa_service: QAService) -> None:
    config.OPENAI_API_KEY = ""
    entry = qa_service.ask("How does authenticate password work?")
    # Should find snippets → confidence > 0
    assert entry.confidence > 0.0


def test_ask_no_matching_snippets_flagged(qa_service: QAService) -> None:
    config.OPENAI_API_KEY = ""
    entry = qa_service.ask("Tell me about the billing module invoices")
    # No relevant snippet → should be flagged
    assert entry.is_flagged is True


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_ask_saves_to_history(qa_service: QAService) -> None:
    config.OPENAI_API_KEY = ""
    qa_service.ask("How does authentication work?")
    history = qa_service.get_history()
    assert len(history) == 1
    assert history[0].question == "How does authentication work?"


def test_multiple_asks_all_saved(qa_service: QAService) -> None:
    config.OPENAI_API_KEY = ""
    qa_service.ask("How does authentication work?")
    qa_service.ask("What does hash password do here?")
    history = qa_service.get_history()
    assert len(history) == 2


# ---------------------------------------------------------------------------
# Flagging and resolution
# ---------------------------------------------------------------------------

def test_get_flagged_returns_flagged_only(qa_service: QAService) -> None:
    config.OPENAI_API_KEY = ""
    # This should be flagged (no matching snippets)
    qa_service.ask("Completely unrelated question about invoices today")
    flagged = qa_service.get_flagged()
    assert all(e.is_flagged for e in flagged)


def test_resolve_flag_removes_from_flagged(qa_service: QAService) -> None:
    config.OPENAI_API_KEY = ""
    qa_service.ask("Completely unrelated question about invoices today")
    flagged = qa_service.get_flagged()
    assert len(flagged) > 0

    qa_service.resolve_flag(flagged[0].entry_id)
    remaining = qa_service.get_flagged()
    assert all(e.entry_id != flagged[0].entry_id for e in remaining)


# ---------------------------------------------------------------------------
# AI error handling
# ---------------------------------------------------------------------------

def test_ai_service_error_propagates(tmp_path: Path, knowledge_service_with_index: KnowledgeService) -> None:
    repo = QARepository(path=tmp_path / "qa2.json")

    svc = QAService(knowledge_service=knowledge_service_with_index, repo=repo)

    with patch.object(svc, "_call_ai", side_effect=AIServiceError("API timeout")):
        with pytest.raises(AIServiceError, match="API timeout"):
            svc.ask("How does authentication work?")
