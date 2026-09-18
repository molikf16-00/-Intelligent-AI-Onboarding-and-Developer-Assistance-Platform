"""
Tests for ChecklistService.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from onboarding_platform.exceptions import ChecklistNotFoundError, ItemNotFoundError
from onboarding_platform.models import ChecklistItem, DeveloperProfile
from onboarding_platform.repositories import ChecklistRepository
from onboarding_platform.services.checklist_service import ChecklistService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def templates_path(tmp_path: Path) -> Path:
    """Write a minimal template file for testing."""
    templates = {
        "default": [
            {"title": "Read README", "description": "Read the project README.", "category": "Setup"},
            {"title": "Meet buddy", "description": "Meet your buddy.", "category": "Team Norms"},
        ],
        "Backend Engineer": [
            {"title": "Review DB schema", "description": "Understand the schema.", "category": "Learning"},
        ],
    }
    path = tmp_path / "templates.json"
    path.write_text(json.dumps(templates))
    return path


@pytest.fixture
def service(tmp_path: Path, templates_path: Path) -> ChecklistService:
    repo = ChecklistRepository(path=tmp_path / "checklist.json")
    return ChecklistService(repo=repo, templates_path=templates_path)


def _make_profile(role: str = "Backend Engineer", team: str = "Platform") -> DeveloperProfile:
    return DeveloperProfile(
        name="Alice",
        role=role,
        team=team,
        start_date=date.today(),
    )


# ---------------------------------------------------------------------------
# generate_checklist
# ---------------------------------------------------------------------------

def test_generate_checklist_backend(service: ChecklistService) -> None:
    profile = _make_profile("Backend Engineer")
    items = service.generate_checklist(profile)

    titles = [i.title for i in items]
    # Default items present
    assert "Read README" in titles
    assert "Meet buddy" in titles
    # Role-specific item present
    assert "Review DB schema" in titles


def test_generate_checklist_unknown_role_falls_back_to_default(
    service: ChecklistService,
) -> None:
    profile = _make_profile("Data Engineer")  # not in test templates
    items = service.generate_checklist(profile)
    titles = [i.title for i in items]
    assert "Read README" in titles
    assert len(items) == 2  # only default items


def test_generate_checklist_no_duplicates(service: ChecklistService) -> None:
    profile = _make_profile("Backend Engineer")
    items = service.generate_checklist(profile)
    titles = [i.title for i in items]
    assert len(titles) == len(set(titles))


def test_generate_checklist_persisted(service: ChecklistService) -> None:
    profile = _make_profile("Backend Engineer")
    service.generate_checklist(profile)
    loaded = service.get_checklist()
    assert len(loaded) == 3


# ---------------------------------------------------------------------------
# get_checklist — before generation
# ---------------------------------------------------------------------------

def test_get_checklist_raises_if_not_generated(service: ChecklistService) -> None:
    with pytest.raises(ChecklistNotFoundError):
        service.get_checklist()


# ---------------------------------------------------------------------------
# mark_complete / mark_incomplete
# ---------------------------------------------------------------------------

def test_mark_complete(service: ChecklistService) -> None:
    profile = _make_profile()
    items = service.generate_checklist(profile)
    first_id = items[0].item_id

    updated = service.mark_complete(first_id)
    assert updated.is_complete is True
    assert updated.completed_at is not None

    # Persisted
    reloaded = service.get_checklist()
    match = next(i for i in reloaded if i.item_id == first_id)
    assert match.is_complete is True


def test_mark_incomplete(service: ChecklistService) -> None:
    profile = _make_profile()
    items = service.generate_checklist(profile)
    first_id = items[0].item_id
    service.mark_complete(first_id)
    updated = service.mark_incomplete(first_id)
    assert updated.is_complete is False
    assert updated.completed_at is None


def test_mark_complete_unknown_id(service: ChecklistService) -> None:
    service.generate_checklist(_make_profile())
    with pytest.raises(ItemNotFoundError):
        service.mark_complete("nonexistent-id")


# ---------------------------------------------------------------------------
# get_progress
# ---------------------------------------------------------------------------

def test_get_progress_initial(service: ChecklistService) -> None:
    service.generate_checklist(_make_profile())
    progress = service.get_progress()
    assert progress["complete"] == 0
    assert progress["total"] == 3
    assert progress["percent"] == 0.0


def test_get_progress_after_completion(service: ChecklistService) -> None:
    items = service.generate_checklist(_make_profile())
    service.mark_complete(items[0].item_id)
    progress = service.get_progress()
    assert progress["complete"] == 1
    assert progress["percent"] == pytest.approx(33.3, abs=0.2)


def test_get_progress_all_complete(service: ChecklistService) -> None:
    items = service.generate_checklist(_make_profile())
    for item in items:
        service.mark_complete(item.item_id)
    progress = service.get_progress()
    assert progress["percent"] == 100.0


def test_get_progress_no_checklist_returns_zeros(service: ChecklistService) -> None:
    progress = service.get_progress()
    assert progress == {"total": 0, "complete": 0, "percent": 0.0, "by_category": {}}
