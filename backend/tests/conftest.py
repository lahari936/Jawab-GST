import os
import tempfile
from pathlib import Path

# Must run before app.models creates its engine. Keeps tests off the real Postgres.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

SAMPLES = Path(__file__).resolve().parents[2] / "samples" / "jawab"
