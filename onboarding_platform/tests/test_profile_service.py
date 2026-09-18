"""
Tests for ProfileService.
"""
from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from onboarding_platform.exceptions import (
    ProfileAlreadyExistsError,
    ValidationError,
)
from onboarding_platform.models import DeveloperProfile
from onboarding_platform.repositories import ProfileRepository
from onboarding_platform.services.profile_service import ProfileService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_profile_path(tmp_path: Path) -> Path:
    return tmp_path / "profile.json"


@pytest.fixture
def service(tmp_profile_path: Path) -> ProfileService:
    repo = ProfileRepository(path=tmp_profile_path)
    return ProfileService(repo=repo)


# ---------------------------------------------------------------------------
# create_profile — happy path
# ---------------------------------------------------------------------------

def test_create_profile_success(service: ProfileService) -> None:
    profile = service.create_profile(
        name="Alice Smith",
        role="Backend Engineer",
        team="Platform",
        start_date=date.today(),
    )
    assert isinstance(profile, DeveloperProfile)
    assert profile.name == "Alice Smith"
    assert profile.role == "Backend Engineer"
    assert profile.team == "Platform"


def test_create_profile_persisted(service: ProfileService, tmp_profile_path: Path) -> None:
    service.create_profile("Bob Jones", "Frontend Engineer", "Web", date.today())
    assert tmp_profile_path.exists()
    data = json.loads(tmp_profile_path.read_text())
    assert data["name"] == "Bob Jones"


# ---------------------------------------------------------------------------
# create_profile — duplicate prevention
# ---------------------------------------------------------------------------

def test_create_profile_twice_raises(service: ProfileService) -> None:
    service.create_profile("Alice", "Backend Engineer", "Platform", date.today())
    with pytest.raises(ProfileAlreadyExistsError):
        service.create_profile("Bob", "Frontend Engineer", "Web", date.today())


# ---------------------------------------------------------------------------
# create_profile — validation errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["", "  ", "A", "A" * 101, "123Invalid", "Name@Bad"])
def test_invalid_name(service: ProfileService, name: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        service.create_profile(name, "Backend Engineer", "Platform", date.today())
    assert exc_info.value.field == "name"


def test_invalid_role(service: ProfileService) -> None:
    with pytest.raises(ValidationError) as exc_info:
        service.create_profile("Alice", "Unknown Role", "Platform", date.today())
    assert exc_info.value.field == "role"


def test_invalid_team(service: ProfileService) -> None:
    with pytest.raises(ValidationError) as exc_info:
        service.create_profile("Alice", "Backend Engineer", "Unknown Team", date.today())
    assert exc_info.value.field == "team"


def test_start_date_too_far_in_past(service: ProfileService) -> None:
    old_date = date.today() - timedelta(days=400)
    with pytest.raises(ValidationError) as exc_info:
        service.create_profile("Alice", "Backend Engineer", "Platform", old_date)
    assert exc_info.value.field == "start_date"


def test_start_date_too_far_in_future(service: ProfileService) -> None:
    future_date = date.today() + timedelta(days=100)
    with pytest.raises(ValidationError) as exc_info:
        service.create_profile("Alice", "Backend Engineer", "Platform", future_date)
    assert exc_info.value.field == "start_date"


# ---------------------------------------------------------------------------
# load_profile / delete_profile
# ---------------------------------------------------------------------------

def test_load_profile_none_when_missing(service: ProfileService) -> None:
    assert service.load_profile() is None


def test_load_profile_returns_saved(service: ProfileService) -> None:
    service.create_profile("Alice", "Backend Engineer", "Platform", date.today())
    loaded = service.load_profile()
    assert loaded is not None
    assert loaded.name == "Alice"


def test_delete_profile(service: ProfileService, tmp_profile_path: Path) -> None:
    service.create_profile("Alice", "Backend Engineer", "Platform", date.today())
    assert tmp_profile_path.exists()
    service.delete_profile()
    assert not tmp_profile_path.exists()
