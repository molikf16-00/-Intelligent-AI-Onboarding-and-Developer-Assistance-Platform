"""
DashboardService — aggregates metrics from profile, checklist, and Q&A history
into a single summary dict for the dashboard page.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from onboarding_platform.models import DeveloperProfile
from onboarding_platform.repositories import QARepository
from onboarding_platform.services.checklist_service import ChecklistService


class DashboardService:
    """Computes the summary metrics shown on the progress dashboard."""

    def __init__(
        self,
        checklist_service: ChecklistService,
        qa_repo: Optional[QARepository] = None,
    ) -> None:
        self._checklist = checklist_service
        self._qa_repo = qa_repo or QARepository()

    def get_summary(self, profile: DeveloperProfile) -> dict:
        """
        Returns a dict with:
        - profile: name, role, team, start_date, days_since_start
        - checklist: total, complete, percent, by_category
        - qa: total_questions, flagged_count, resolved_count
        """
        today = date.today()
        days_since_start = (today - profile.start_date).days

        checklist_progress = self._checklist.get_progress()

        qa_history = self._qa_repo.load()
        flagged = [e for e in qa_history if e.is_flagged]
        resolved = [e for e in flagged if e.is_resolved]

        return {
            "profile": {
                "name": profile.name,
                "role": profile.role,
                "team": profile.team,
                "start_date": profile.start_date.isoformat(),
                "days_since_start": days_since_start,
            },
            "checklist": checklist_progress,
            "qa": {
                "total_questions": len(qa_history),
                "flagged_count": len(flagged),
                "resolved_count": len(resolved),
            },
        }
