"""Vercel-compatible WSGI entrypoint for backend-root deployments.

When the Vercel project root is configured as ``backend/``, the platform looks
for ``wsgi.py`` in that directory. The canonical Django WSGI module remains
``backend/backend/wsgi.py``; this file exposes the same callable plus an ``app``
alias expected by Python serverless runtimes.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_wsgi_application()
app = application
