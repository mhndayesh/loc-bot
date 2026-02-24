import os

# Project root is two levels up from this file (src/paths.py)
PROJECT_ROOT = os.path.normpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Common directories
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
CORE_DIR = os.path.join(SRC_DIR, "core")
API_DIR = os.path.join(SRC_DIR, "api")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")
INTEGRATIONS_DIR = os.path.join(PROJECT_ROOT, "integrations")
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
MEMORY_DIR = os.path.join(DATA_DIR, "memory")
CHROMA_DB_PATH = os.path.join(DATA_DIR, "chroma_db")

# Specific files
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
MEMORY_STORAGE_FILE = os.path.join(DATA_DIR, "memory_vault.json")
INSTRUCTIONS_FILE = os.path.join(DATA_DIR, "instructions.json")
JOURNAL_FILE = os.path.join(LOGS_DIR, "JOURNAL.md")
SCRATCHPAD_FILE = os.path.join(LOGS_DIR, "SCRATCHPAD.md")
SUMMARY_FILE = os.path.join(LOGS_DIR, "SUMMARY.md")
SKILLS_MD_FILE = os.path.join(DOCS_DIR, "SKILLS.md")
MAP_MD_FILE = os.path.join(DOCS_DIR, "ARCHITECTURE.md")
SOUL_FILE = os.path.join(LOGS_DIR, "SOUL.md")
USER_GUIDE_FILE = os.path.join(DOCS_DIR, "USER_GUIDE.md")

def ensure_dirs():
    """Ensure all required directories exist."""
    for d in (SRC_DIR, CORE_DIR, API_DIR, FRONTEND_DIR, CONFIG_DIR, DATA_DIR, LOGS_DIR, DOCS_DIR, SCRIPTS_DIR, SKILLS_DIR, INTEGRATIONS_DIR, WORKSPACE_DIR, MEMORY_DIR, CHROMA_DB_PATH):
        os.makedirs(d, exist_ok=True)
