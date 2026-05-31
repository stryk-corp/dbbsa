"""WSGI config for DBBSA project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neural_village.settings')

application = get_wsgi_application()
