"""
ProfileService — business logic for creating and loading developer profiles.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from onboarding_platform import config
from onboarding_platform.exceptions import (
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    ValidationError,
)
from onboarding_platform.models import DeveloperProfile
from onboarding_platform.repositories import ProfileRepository


class ProfileService:
    """Manages the single developer profile for the session."""

    def __init__(self, repo: Optional[ProfileRepository] = None) -> None:
        self._repo = repo or ProfileRepository()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        role: str,
        team: str,
        start_date: date,
    ) -> DeveloperProfile:
        """
        Validate inputs, create a DeveloperProfile, and persist it.
        Raises ProfileAlreadyExistsError if a profile already exists.
        """
        if self._repo.exists():
            raise ProfileAlreadyExistsError(
                "A profile already exists. Reset it before creating a new one."
            )
        self._validate_name(name)
        self._validate_role(role)
        self._validate_team(team)
        self._validate_start_date(start_date)

        profile = DeveloperProfile(
            name=name.strip(),
            role=role,
            team=team,
            start_date=start_date,
        )
        self._repo.save(profile)
        return profile

    def load_profile(self) -> Optional[DeveloperProfile]:
        """Return the saved profile, or None if none exists yet."""
        return self._repo.load()

    def profile_exists(self) -> bool:
        return self._repo.exists()

    def delete_profile(self) -> None:
        """Remove the current profile (used for 'reset session')."""
        self._repo.delete()

    # ------------------------------------------------------------------
    # Private validators
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_name(name: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("name", "Name cannot be empty.")
        if len(name) < 2:
            raise ValidationError("name", "Name must be at least 2 characters.")
        if len(name) > 100:
            raise ValidationError("name", "Name cannot exceed 100 characters.")
        if not re.match(r"^[A-Za-z\s'\-]+$", name):
            raise ValidationError(
                "name", "Name may only contain letters, spaces, hyphens, and apostrophes."
            )

    @staticmethod
    def _validate_role(role: str) -> None:
        if role not in config.ALLOWED_ROLES:
            raise ValidationError(
                "role",
                f"Role must be one of: {', '.join(config.ALLOWED_ROLES)}",
            )

    @staticmethod
    def _validate_team(team: str) -> None:
        if team not in config.ALLOWED_TEAMS:
            raise ValidationError(
                "team",
                f"Team must be one of: {', '.join(config.ALLOWED_TEAMS)}",
            )

    @staticmethod
    def _validate_start_date(start_date: date) -> None:
        today = date.today()
        earliest = today - timedelta(days=config.START_DATE_MAX_PAST_DAYS)
        latest = today + timedelta(days=config.START_DATE_MAX_FUTURE_DAYS)
        if start_date < earliest:
            raise ValidationError(
                "start_date",
                f"Start date cannot be more than {config.START_DATE_MAX_PAST_DAYS} days in the past.",
            )
        if start_date > latest:
            raise ValidationError(
                "start_date",
                f"Start date cannot be more than {config.START_DATE_MAX_FUTURE_DAYS} days in the future.",
            )
