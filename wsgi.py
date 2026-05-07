"""Vercel-compatible WSGI entrypoint for repo-root backend deployments.

The Django project lives in ``backend/backend``. Vercel's zero-config Django
scanner looks for a top-level ``wsgi.py`` when the project root is the repo
root, so this wrapper adds the backend directory to ``sys.path`` and exposes
both ``application`` and ``app``.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
