"""
Repository layer — all JSON read/write operations live here.
Services call these repositories; nothing else touches the files directly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from onboarding_platform.models import (
    ChecklistItem,
    DeveloperProfile,
    KnowledgeSource,
    QAEntry,
)
from onboarding_platform import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict | list | None:
    """Return parsed JSON from *path*, or None if the file doesn't exist."""
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, data: dict | list) -> None:
    """Serialise *data* to *path* (creates the file if needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# ProfileRepository
# ---------------------------------------------------------------------------

class ProfileRepository:
    """Persist a single DeveloperProfile to JSON."""

    def __init__(self, path: Path = config.PROFILE_FILE) -> None:
        self._path = path

    def save(self, profile: DeveloperProfile) -> None:
        _write_json(self._path, profile.to_dict())

    def load(self) -> Optional[DeveloperProfile]:
        data = _read_json(self._path)
        if data is None:
            return None
        return DeveloperProfile.from_dict(data)  # type: ignore[arg-type]

    def exists(self) -> bool:
        return self._path.exists()

    def delete(self) -> None:
        if self._path.exists():
            self._path.unlink()


# ---------------------------------------------------------------------------
# ChecklistRepository
# ---------------------------------------------------------------------------

class ChecklistRepository:
    """Persist the list of ChecklistItems to JSON."""

    def __init__(self, path: Path = config.CHECKLIST_FILE) -> None:
        self._path = path

    def save(self, items: list[ChecklistItem]) -> None:
        _write_json(self._path, [item.to_dict() for item in items])

    def load(self) -> list[ChecklistItem]:
        data = _read_json(self._path)
        if not data:
            return []
        return [ChecklistItem.from_dict(d) for d in data]  # type: ignore[arg-type]

    def exists(self) -> bool:
        return self._path.exists()


# ---------------------------------------------------------------------------
# QARepository
# ---------------------------------------------------------------------------

class QARepository:
    """Persist Q&A history to JSON (most recent first, capped at MAX_QA_HISTORY)."""

    def __init__(self, path: Path = config.QA_HISTORY_FILE) -> None:
        self._path = path

    def append(self, entry: QAEntry) -> None:
        history = self.load()
        history.insert(0, entry)  # newest first
        if len(history) > config.MAX_QA_HISTORY:
            history = history[: config.MAX_QA_HISTORY]
        _write_json(self._path, [e.to_dict() for e in history])

    def load(self) -> list[QAEntry]:
        data = _read_json(self._path)
        if not data:
            return []
        return [QAEntry.from_dict(d) for d in data]  # type: ignore[arg-type]

    def update(self, updated: QAEntry) -> None:
        """Persist changes to a single entry (e.g. resolve flag)."""
        history = self.load()
        for i, entry in enumerate(history):
            if entry.entry_id == updated.entry_id:
                history[i] = updated
                break
        _write_json(self._path, [e.to_dict() for e in history])

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()


# ---------------------------------------------------------------------------
# KnowledgeRepository
# ---------------------------------------------------------------------------

class KnowledgeRepository:
    """Persist knowledge-source metadata to JSON."""

    def __init__(self, path: Path = config.KNOWLEDGE_META_FILE) -> None:
        self._path = path

    def save(self, source: KnowledgeSource) -> None:
        _write_json(self._path, source.to_dict())

    def load(self) -> Optional[KnowledgeSource]:
        data = _read_json(self._path)
        if data is None:
            return None
        return KnowledgeSource.from_dict(data)  # type: ignore[arg-type]

    def exists(self) -> bool:
        return self._path.exists()
