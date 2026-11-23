"""Test configuration: never touch the demo database during tests."""
import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.mkdtemp(prefix="northstar-tests-")) / "api.sqlite"
os.environ["NORTHSTAR_DB"] = str(TEST_DB)
os.environ.pop("DATABASE_URL", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ADMIN_TOKEN", None)
