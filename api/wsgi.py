"""Vercel-compatible WSGI entrypoint at api/wsgi.py.

Some Vercel Django templates and scanners prefer an ``api/wsgi.py`` entrypoint.
The actual Django project lives under ``backend/backend``.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = BASE_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
