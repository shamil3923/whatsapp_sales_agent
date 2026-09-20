"""
Shared pytest setup.

Keeps the suite hermetic: every run gets its own SQLite database and telemetry
log in a temporary directory, so tests never read or write the repository's
``data/`` directory and cannot see each other's state.

These variables are set at import time because ``whatsapp_integration``
constructs its bot (and therefore its ConversationMemory) at module import,
which happens when the first test module is collected.
"""
import os
import sys
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="whatsapp-agent-tests-")

os.environ.setdefault("AGENT_DB_PATH", os.path.join(_TMP_DIR, "agent.db"))
os.environ.setdefault("TELEMETRY_LOG_PATH", os.path.join(_TMP_DIR, "turns.jsonl"))
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "sales_agent_verify_token")

# Test modules import the application by module name.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
