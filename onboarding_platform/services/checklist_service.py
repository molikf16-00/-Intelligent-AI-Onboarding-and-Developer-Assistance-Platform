"""
ChecklistService — generates a role-based onboarding checklist from a JSON
template file and manages item completion state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from onboarding_platform import config
from onboarding_platform.exceptions import ChecklistNotFoundError, ItemNotFoundError
from onboarding_platform.models import ChecklistItem, DeveloperProfile
from onboarding_platform.repositories import ChecklistRepository


class ChecklistService:
    """Generates and manages the onboarding checklist for the active profile."""

    def __init__(
        self,
        repo: Optional[ChecklistRepository] = None,
        templates_path: Optional[Path] = None,
    ) -> None:
        self._repo = repo or ChecklistRepository()
        self._templates_path = templates_path or config.TEMPLATES_FILE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_checklist(self, profile: DeveloperProfile) -> list[ChecklistItem]:
        """
        Generate a checklist from the template for *profile.role*.
        Falls back to the 'default' template if the role has no specific entry.

        Merges: default items FIRST, then role-specific items (de-duplicated by title).
        Saves and returns the list.
        """
        templates = self._load_templates()

        default_items = templates.get("default", [])
        role_items = templates.get(profile.role, [])

        # De-duplicate: role items override default items with the same title
        seen_titles: set[str] = set()
        merged: list[dict] = []
        for raw in role_items + default_items:
            if raw["title"] not in seen_titles:
                seen_titles.add(raw["title"])
                merged.append(raw)

        # role items come first in the merged list (already inserted above)
        # re-sort so role-specific items appear after defaults for readability
        role_titles = {r["title"] for r in role_items}
        default_part = [r for r in merged if r["title"] not in role_titles]
        role_part = [r for r in merged if r["title"] in role_titles]
        ordered = default_part + role_part

        items = [
            ChecklistItem(
                title=raw["title"],
                description=raw.get("description", ""),
                category=raw.get("category", "General"),
                role=profile.role,
                team=profile.team,
            )
            for raw in ordered
        ]

        self._repo.save(items)
        return items

    def get_checklist(self) -> list[ChecklistItem]:
        """Load the persisted checklist. Raises ChecklistNotFoundError if none exists."""
        if not self._repo.exists():
            raise ChecklistNotFoundError(
                "No checklist found. Generate one first via your profile."
            )
        return self._repo.load()

    def mark_complete(self, item_id: str) -> ChecklistItem:
        """Mark an item complete. Returns the updated item."""
        items = self._get_items_or_raise()
        item = self._find_item(items, item_id)
        item.is_complete = True
        item.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self._repo.save(items)
        return item

    def mark_incomplete(self, item_id: str) -> ChecklistItem:
        """Unmark a completed item."""
        items = self._get_items_or_raise()
        item = self._find_item(items, item_id)
        item.is_complete = False
        item.completed_at = None
        self._repo.save(items)
        return item

    def get_progress(self) -> dict:
        """
        Return a progress summary dict:
        {
            "total": int,
            "complete": int,
            "percent": float,
            "by_category": {category: {"total": int, "complete": int}}
        }
        """
        if not self._repo.exists():
            return {"total": 0, "complete": 0, "percent": 0.0, "by_category": {}}

        items = self._repo.load()
        total = len(items)
        complete = sum(1 for i in items if i.is_complete)
        percent = (complete / total * 100) if total > 0 else 0.0

        by_category: dict[str, dict] = {}
        for item in items:
            cat = item.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "complete": 0}
            by_category[cat]["total"] += 1
            if item.is_complete:
                by_category[cat]["complete"] += 1

        return {
            "total": total,
            "complete": complete,
            "percent": round(percent, 1),
            "by_category": by_category,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_templates(self) -> dict:
        if not self._templates_path.exists():
            return {"default": []}
        with self._templates_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _get_items_or_raise(self) -> list[ChecklistItem]:
        if not self._repo.exists():
            raise ChecklistNotFoundError("No checklist found.")
        return self._repo.load()

    @staticmethod
    def _find_item(items: list[ChecklistItem], item_id: str) -> ChecklistItem:
        for item in items:
            if item.item_id == item_id:
                return item
        raise ItemNotFoundError(f"Checklist item '{item_id}' not found.")
