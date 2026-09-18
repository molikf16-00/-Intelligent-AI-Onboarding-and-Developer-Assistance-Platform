"""
QAService — retrieval-augmented Q&A using the OpenAI Chat API.

Flow:
  1. Retrieve relevant code snippets via KnowledgeService.
  2. Build a prompt with those snippets as context.
  3. Call the OpenAI API.
  4. If confidence < threshold OR no snippets found → flag the entry.
  5. Persist and return the QAEntry.
"""
from __future__ import annotations

from typing import Optional

from onboarding_platform import config
from onboarding_platform.exceptions import AIServiceError, ValidationError
from onboarding_platform.models import QAEntry
from onboarding_platform.repositories import QARepository
from onboarding_platform.services.knowledge_service import KnowledgeService


_SYSTEM_PROMPT = (
    "You are an expert developer onboarding assistant. "
    "Answer the developer's question using ONLY the code snippets provided as context. "
    "If the snippets do not contain enough information to answer, say so clearly. "
    "Be concise and helpful."
)


class QAService:
    """Handles natural-language Q&A grounded in the indexed codebase."""

    def __init__(
        self,
        knowledge_service: KnowledgeService,
        repo: Optional[QARepository] = None,
    ) -> None:
        self._knowledge = knowledge_service
        self._repo = repo or QARepository()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ask(self, question: str) -> QAEntry:
        """
        Ask a question.  Returns a persisted QAEntry.

        * Validates the question.
        * Retrieves relevant snippets.
        * Calls the AI (or generates a fallback if the API key is missing).
        * Flags low-confidence answers.
        """
        question = question.strip()
        self._validate_question(question)

        # --- Retrieval ---
        try:
            snippets, confidence = self._knowledge.retrieve(question)
        except Exception:
            snippets, confidence = [], 0.0

        # --- AI call ---
        try:
            answer = self._call_ai(question, snippets)
        except AIServiceError:
            raise
        except Exception as exc:
            raise AIServiceError(f"Unexpected error during AI call: {exc}") from exc

        # --- Flagging ---
        is_flagged = (confidence < config.CONFIDENCE_THRESHOLD) or (not snippets)

        entry = QAEntry(
            question=question,
            answer=answer,
            confidence=confidence,
            is_flagged=is_flagged,
            source_chunks=snippets,
        )
        self._repo.append(entry)
        return entry

    def get_history(self) -> list[QAEntry]:
        return self._repo.load()

    def get_flagged(self) -> list[QAEntry]:
        return [e for e in self._repo.load() if e.is_flagged and not e.is_resolved]

    def resolve_flag(self, entry_id: str) -> None:
        """Mark a flagged entry as resolved by a human reviewer."""
        history = self._repo.load()
        for entry in history:
            if entry.entry_id == entry_id:
                entry.is_resolved = True
                self._repo.update(entry)
                return

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_question(question: str) -> None:
        if not question:
            raise ValidationError("question", "Question cannot be empty.")
        if len(question) < 5:
            raise ValidationError("question", "Question must be at least 5 characters.")
        if len(question) > 1000:
            raise ValidationError("question", "Question cannot exceed 1000 characters.")

    @staticmethod
    def _build_prompt(question: str, snippets: list[str]) -> str:
        if snippets:
            context_block = "\n\n---\n\n".join(snippets)
            return (
                f"CONTEXT FROM CODEBASE:\n\n{context_block}\n\n"
                f"---\n\nDEVELOPER QUESTION:\n{question}"
            )
        return (
            "No relevant code snippets were found in the indexed codebase.\n\n"
            f"DEVELOPER QUESTION:\n{question}"
        )

    def _call_ai(self, question: str, snippets: list[str]) -> str:
        """
        Call the OpenAI Chat Completions API.
        Falls back to a clear message if no API key is configured.
        """
        if not config.OPENAI_API_KEY:
            return self._no_api_key_response(question, snippets)

        try:
            import openai  # imported here so the rest of the app works without openai installed

            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            prompt = self._build_prompt(question, snippets)
            response = client.chat.completions.create(
                model=config.AI_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
                temperature=0.2,
            )
            return response.choices[0].message.content or "(empty response)"
        except Exception as exc:
            raise AIServiceError(f"OpenAI API error: {exc}") from exc

    @staticmethod
    def _no_api_key_response(question: str, snippets: list[str]) -> str:
        """
        When no API key is set, return a helpful demo response that still
        shows the retrieved snippets so the user can see the retrieval working.
        """
        if snippets:
            snippet_preview = snippets[0][:400]
            return (
                "⚠️ **No OpenAI API key configured.**\n\n"
                "The retrieval step found the following relevant snippet:\n\n"
                f"```\n{snippet_preview}\n```\n\n"
                "To get an AI-generated answer, add your OpenAI API key to "
                "`config.py` or set the `OPENAI_API_KEY` environment variable."
            )
        return (
            "⚠️ **No OpenAI API key configured** and no relevant snippets were found.\n\n"
            "To get an AI-generated answer:\n"
            "1. Add your OpenAI API key to `config.py` or set `OPENAI_API_KEY`.\n"
            "2. Make sure a knowledge source has been indexed."
        )
