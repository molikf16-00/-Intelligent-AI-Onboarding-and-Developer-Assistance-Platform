"""
Application-wide configuration constants.
Edit OPENAI_API_KEY here or set the environment variable OPENAI_API_KEY.
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / ".data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_FILE = DATA_DIR / "profile.json"
CHECKLIST_FILE = DATA_DIR / "checklist.json"
QA_HISTORY_FILE = DATA_DIR / "qa_history.json"
KNOWLEDGE_META_FILE = DATA_DIR / "knowledge_meta.json"
TEMPLATES_FILE = BASE_DIR / "checklist_templates.json"

# ---------------------------------------------------------------------------
# AI / retrieval settings
# ---------------------------------------------------------------------------
# Set your OpenAI API key here OR via the OPENAI_API_KEY environment variable.
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Model to use for chat completions
AI_MODEL: str = "gpt-4o-mini"

# Confidence threshold: answers with a retrieval score below this are flagged
CONFIDENCE_THRESHOLD: float = 0.25

# Maximum number of snippet characters sent to the AI per answer
MAX_SNIPPET_CHARS: int = 3000

# Maximum Q&A history entries kept on disk
MAX_QA_HISTORY: int = 200

# Supported file extensions for knowledge indexing
SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    ".py", ".md", ".txt", ".js", ".ts", ".json", ".yaml", ".yml", ".rst"
)

# Maximum single file size to index (bytes) — 1 MB
MAX_FILE_BYTES: int = 1 * 1024 * 1024

# ---------------------------------------------------------------------------
# Profile validation
# ---------------------------------------------------------------------------
ALLOWED_ROLES: list[str] = [
    "Backend Engineer",
    "Frontend Engineer",
    "Full-Stack Engineer",
    "DevOps / Platform Engineer",
    "Data Engineer",
    "QA / Test Engineer",
    "Technical Lead",
]

ALLOWED_TEAMS: list[str] = [
    "Platform",
    "Mobile",
    "Web",
    "Data",
    "Infrastructure",
    "QA",
    "General",
]

START_DATE_MAX_FUTURE_DAYS: int = 90
START_DATE_MAX_PAST_DAYS: int = 365
