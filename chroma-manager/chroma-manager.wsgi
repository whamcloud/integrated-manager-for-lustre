import os
import sys

SITE_ROOT = os.path.dirname (os.path.realpath (__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.insert (0, SITE_ROOT)

os.environ['CELERY_LOADER'] = 'django'

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler ()
