import os
import sys


SITE_ROOT = os.path.dirname (os.path.realpath (__file__))
ACTIVATE_VIRTUALENV = "%s/../env/bin/activate_this.py" % SITE_ROOT

execfile(ACTIVATE_VIRTUALENV, dict(__file__ = ACTIVATE_VIRTUALENV))

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.insert (0, SITE_ROOT)

os.environ['CELERY_LOADER'] = 'django'

from chroma_core.services.log import log_set_filename
log_set_filename('http.log')

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler ()
