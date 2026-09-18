"""
Custom exceptions for the Onboarding Platform.
Each exception maps to a specific business rule violation or error condition.
"""


class OnboardingPlatformError(Exception):
    """Base exception for all platform errors."""


class ProfileAlreadyExistsError(OnboardingPlatformError):
    """Raised when trying to create a profile when one already exists."""


class ProfileNotFoundError(OnboardingPlatformError):
    """Raised when a feature is accessed before a profile has been created."""


class KnowledgeSourceNotReadyError(OnboardingPlatformError):
    """Raised when Q&A is attempted before a knowledge index has been built."""


class InvalidFileTypeError(OnboardingPlatformError):
    """Raised when an unsupported file type is provided for indexing."""


class PathNotFoundError(OnboardingPlatformError):
    """Raised when a local directory path does not exist."""


class ValidationError(OnboardingPlatformError):
    """Raised when a field fails input validation."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"Validation error on '{field}': {message}")


class AIServiceError(OnboardingPlatformError):
    """Raised when the AI API call fails or times out."""


class ChecklistNotFoundError(OnboardingPlatformError):
    """Raised when the checklist is accessed before it has been generated."""


class ItemNotFoundError(OnboardingPlatformError):
    """Raised when toggling a checklist item that does not exist."""
