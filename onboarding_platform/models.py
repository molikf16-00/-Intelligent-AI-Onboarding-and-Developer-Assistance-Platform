"""
Pure data containers for the Onboarding Platform.
All classes use dataclasses with no business logic — they are plain data holders.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    LOCAL_DIR = "LOCAL_DIR"
    UPLOADED_FILE = "UPLOADED_FILE"


@dataclass
class DeveloperProfile:
    name: str
    role: str
    team: str
    start_date: date
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "role": self.role,
            "team": self.team,
            "start_date": self.start_date.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeveloperProfile":
        return cls(
            profile_id=data["profile_id"],
            name=data["name"],
            role=data["role"],
            team=data["team"],
            start_date=date.fromisoformat(data["start_date"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class KnowledgeSource:
    path: str
    source_type: SourceType
    indexed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    file_count: int = 0
    source_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "path": self.path,
            "source_type": self.source_type.value,
            "indexed_at": self.indexed_at.isoformat(),
            "file_count": self.file_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeSource":
        return cls(
            source_id=data["source_id"],
            path=data["path"],
            source_type=SourceType(data["source_type"]),
            indexed_at=datetime.fromisoformat(data["indexed_at"]),
            file_count=data["file_count"],
        )


@dataclass
class QAEntry:
    question: str
    answer: str
    confidence: float
    is_flagged: bool
    source_chunks: list[str] = field(default_factory=list)
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    is_resolved: bool = False

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "is_flagged": self.is_flagged,
            "is_resolved": self.is_resolved,
            "source_chunks": self.source_chunks,
            "asked_at": self.asked_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QAEntry":
        return cls(
            entry_id=data["entry_id"],
            question=data["question"],
            answer=data["answer"],
            confidence=data["confidence"],
            is_flagged=data["is_flagged"],
            is_resolved=data.get("is_resolved", False),
            source_chunks=data.get("source_chunks", []),
            asked_at=datetime.fromisoformat(data["asked_at"]),
        )


@dataclass
class ChecklistItem:
    title: str
    description: str
    category: str
    role: str
    team: Optional[str] = None
    is_complete: bool = False
    completed_at: Optional[datetime] = None
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "role": self.role,
            "team": self.team,
            "is_complete": self.is_complete,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChecklistItem":
        return cls(
            item_id=data["item_id"],
            title=data["title"],
            description=data["description"],
            category=data["category"],
            role=data["role"],
            team=data.get("team"),
            is_complete=data["is_complete"],
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )
