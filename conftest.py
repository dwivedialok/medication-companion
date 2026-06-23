"""
Project-root conftest.

Ensures tests can use either import style:
  - `from tools.x import ...`     (existing unit tests; needs `backend/` on sys.path)
  - `from backend.x import ...`   (scaffold integration tests; needs project root on sys.path)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"

for p in (ROOT, BACKEND):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
