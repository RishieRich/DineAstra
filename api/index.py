"""Vercel entrypoint.

Vercel resolves a Python function from this file and builds the whole FastAPI
app into one function. The app's routes are already mounted under /api, and
vercel.json rewrites /api/* here, so the paths the function sees are the paths
the app expects -- no prefix juggling.

Everything else on the domain is served as the static Vite build.
"""

import sys
from pathlib import Path

# The function's working directory is the bundle root; the app is imported as
# a package from there, so the root has to be importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ui.backend.main import app  # noqa: E402

__all__ = ["app"]
