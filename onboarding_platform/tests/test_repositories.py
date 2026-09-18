"""
Tests for repositories (ProfileRepository, ChecklistRepository, QARepository, KnowledgeRepository).
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from onboarding_platform.models import (
    ChecklistItem,
    DeveloperProfile,
    KnowledgeSource,
    QAEntry,
    SourceType,
)
from onboarding_platform.repositories import (
    ChecklistRepository,
    KnowledgeRepository,
    ProfileRepository,
    QARepository,
)
from onboarding_platform import config


# ---------------------------------------------------------------------------
# ProfileRepository
# ---------------------------------------------------------------------------

def test_profile_repo_save_and_load(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    repo = ProfileRepository(path=path)
    profile = DeveloperProfile(
        name="Alice", role="Backend Engineer", team="Platform", start_date=date.today()
    )
    repo.save(profile)
    loaded = repo.load()
    assert loaded is not None
    assert loaded.name == "Alice"
    assert loaded.profile_id == profile.profile_id


def test_profile_repo_load_missing_returns_none(tmp_path: Path) -> None:
    repo = ProfileRepository(path=tmp_path / "nope.json")
    assert repo.load() is None


def test_profile_repo_exists(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    repo = ProfileRepository(path=path)
    assert not repo.exists()
    repo.save(DeveloperProfile("A", "Backend Engineer", "Platform", date.today()))
    assert repo.exists()


def test_profile_repo_delete(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    repo = ProfileRepository(path=path)
    repo.save(DeveloperProfile("A", "Backend Engineer", "Platform", date.today()))
    repo.delete()
    assert not path.exists()


# ---------------------------------------------------------------------------
# ChecklistRepository
# ---------------------------------------------------------------------------

def test_checklist_repo_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "cl.json"
    repo = ChecklistRepository(path=path)
    items = [
        ChecklistItem(title="Task 1", description="Desc 1", category="Setup", role="Backend Engineer"),
        ChecklistItem(title="Task 2", description="Desc 2", category="Learning", role="Backend Engineer"),
    ]
    repo.save(items)
    loaded = repo.load()
    assert len(loaded) == 2
    assert loaded[0].title == "Task 1"


def test_checklist_repo_load_empty(tmp_path: Path) -> None:
    repo = ChecklistRepository(path=tmp_path / "none.json")
    assert repo.load() == []


# ---------------------------------------------------------------------------
# QARepository
# ---------------------------------------------------------------------------

def _make_entry(question: str = "test?") -> QAEntry:
    return QAEntry(
        question=question,
        answer="answer",
        confidence=0.8,
        is_flagged=False,
    )


def test_qa_repo_append_and_load(tmp_path: Path) -> None:
    repo = QARepository(path=tmp_path / "qa.json")
    e1 = _make_entry("Q1?")
    e2 = _make_entry("Q2?")
    repo.append(e1)
    repo.append(e2)
    history = repo.load()
    # newest first
    assert history[0].question == "Q2?"
    assert history[1].question == "Q1?"


def test_qa_repo_update_entry(tmp_path: Path) -> None:
    repo = QARepository(path=tmp_path / "qa.json")
    entry = _make_entry("flagged?")
    entry.is_flagged = True
    repo.append(entry)

    entry.is_resolved = True
    repo.update(entry)

    loaded = repo.load()
    assert loaded[0].is_resolved is True


def test_qa_repo_caps_at_max(tmp_path: Path) -> None:
    repo = QARepository(path=tmp_path / "qa.json")
    original_max = config.MAX_QA_HISTORY
    config.MAX_QA_HISTORY = 3
    try:
        for i in range(5):
            repo.append(_make_entry(f"Q{i}?"))
        assert len(repo.load()) == 3
    finally:
        config.MAX_QA_HISTORY = original_max


# ---------------------------------------------------------------------------
# KnowledgeRepository
# ---------------------------------------------------------------------------

def test_knowledge_repo_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "km.json"
    repo = KnowledgeRepository(path=path)
    source = KnowledgeSource(path="/some/path", source_type=SourceType.LOCAL_DIR, file_count=10)
    repo.save(source)
    loaded = repo.load()
    assert loaded is not None
    assert loaded.path == "/some/path"
    assert loaded.file_count == 10
    assert loaded.source_type == SourceType.LOCAL_DIR
