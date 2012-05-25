#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import sys
import os
import socket
import logging
import logging.handlers
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

# We require python >= 2.6.5 for http://bugs.python.org/issue4978
if sys.version_info < (2, 6, 5):
    raise EnvironmentError("Python >= 2.6.5 is required")

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'chroma',                 # Or path to database file if using sqlite3.
        'USER': 'root',                  # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        'OPTIONS': {'init_command': 'SET storage_engine=INNODB'}
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "UTC"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory that holds static files.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(SITE_ROOT, 'static')

# URL that handles the static files served from STATIC_ROOT.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# A list of locations of additional static files
STATICFILES_DIRS = ()

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(rpb*-5f69cv=zc#$-bed7^_&8f)ve4dt4chacg$r^89)+%2i*'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS +\
    ("django.core.context_processors.request",
     "chroma_ui.context_processors.app_version")

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

import djcelery
djcelery.setup_loader()

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "chroma"
BROKER_PASSWORD = "chroma123"
BROKER_VHOST = "chromavhost"

CELERY_RESULT_BACKEND = "database"

# HYD-471: This must be set for unit tests to pass in general
SOUTH_TESTS_MIGRATE = False

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'south',
    'r3d',
    'djcelery',
    'tastypie',
    'chroma_core',
    'chroma_api',
    'chroma_ui',
    'chroma_help',
    'benchmark'
    )

OPTIONAL_APPS = ['debug_toolbar', 'django_extensions', 'django_coverage', 'django_nose', 'djsupervisor']
for app in OPTIONAL_APPS:
    import imp
    try:
        imp.find_module(app)
        INSTALLED_APPS = INSTALLED_APPS + (app,)
    except ImportError:
        pass

if 'django_nose' in INSTALLED_APPS:
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = ['--exclude=.*(integration|selenium).*']

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'middleware.TastypieTransactionMiddleware',
)
if 'debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)


def custom_show_toolbar(request):
    return DEBUG

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
    'EXTRA_SIGNALS': [],
    'HIDE_DJANGO_SQL': False,
    'TAG': 'div',
    }

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    )

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        }
    }
}

# Periods given in seconds
AUDIT_PERIOD = 10
JANITOR_PERIOD = 60
PLUGIN_DEFAULT_UPDATE_PERIOD = 5
EMAIL_ALERTS_PERIOD = 300

JOB_MAX_AGE = 3600 * 24 * 7
AUDIT_MAX_AGE = 3600 * 24

SQL_RETRY_PERIOD = 10

LUSTRE_MKFS_OPTIONS_MDT = None
LUSTRE_MKFS_OPTIONS_OST = None

CELERY_ROUTES = (
        {"chroma_core.tasks.audit_all": {"queue": "periodic"}},
        {"chroma_core.tasks.mail_alerts": {"queue": "periodic"}},
        {"chroma_core.tasks.parse_log_entries": {"queue": "parselog"}},
        {"chroma_core.tasks.janitor": {"queue": "periodic"}},

        {"chroma_core.tasks.command_run_jobs": {"queue": "serialize"}},
        {"chroma_core.tasks.command_set_state": {"queue": "serialize"}},
        {"chroma_core.tasks.notify_state": {"queue": "serialize"}},
        {"chroma_core.tasks.add_job": {"queue": "serialize"}},
        {"chroma_core.tasks.complete_job": {"queue": "serialize"}},
        {"chroma_core.tasks.unpaused_job": {"queue": "serialize"}},

        {"chroma_core.tasks.run_job": {"queue": "jobs"}},
        {"chroma_core.tasks.test_host_contact": {"queue": "jobs"}},
        {"chroma_core.tasks.send_alerts_email": {"queue": "jobs"}},
        {"chroma_core.tasks.installation": {"queue": "service"}},
        )

CELERY_TRACK_STARTED = True
CELERY_DISABLE_RATE_LIMITS = True

# CELERY_ACKS_LATE is really important, it makes celery try a task again when a worker
# crashes (only works with proper AMQP backend like RabbitMQ, not DJKombu)
CELERY_ACKS_LATE = True

if DEBUG:
    LOG_PATH = ""
else:
    LOG_PATH = "/var/log/chroma"

LOG_LEVEL = logging.INFO


def setup_log(log_name, filename = None):
    if not filename:
        filename = "%s.log" % log_name

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    path = os.path.join(LOG_PATH, filename)
    handler = logging.handlers.WatchedFileHandler(path)
    handler.setFormatter(logging.Formatter('[%(asctime)s: %(levelname)s/%(name)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
    logger.addHandler(handler)
    if DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(LOG_LEVEL)
    return logger

EMAIL_HOST = None
EMAIL_SUBJECT_PREFIX = "[Chroma Server]"
EMAIL_SENDER = "noreply@%s" % socket.getfqdn()

_plugins_path = os.path.join(os.path.dirname(sys.modules['settings'].__file__), 'chroma_core', 'plugins')
sys.path.append(_plugins_path)
INSTALLED_STORAGE_PLUGINS = ["linux", "linux_network"]
#: Whether to enable debug-level logging across chroma_core.lib.storage_plugin
STORAGE_PLUGIN_DEBUG = DEBUG
#: List of plugins to enable debug-level logging for
STORAGE_PLUGIN_DEBUG_PLUGINS = []

# For django_coverage
COVERAGE_REPORT_HTML_OUTPUT_DIR = '/tmp/test_html'

# If your server isn't serving at port 80 on its FQDN
# SERVER_HTTP_URL = "http://myhost.mydomain:80/"
SERVER_HTTP_URL = None

# If your log server isn't running on this host's FQDN
# LOG_SERVER_HOSTNAME = "mylogserver.mydoman"
LOG_SERVER_HOSTNAME = None

# Maximum latency between server and agent: used to
# check if clocks are 'reasonably' in sync
AGENT_CLOCK_TOLERANCE = 20

# Set to False to require logins even for read-only access
# to chroma_api
ALLOW_ANONYMOUS_READ = True

LOCAL_SETTINGS_FILE = "local_settings.py"

try:
    from production_version import VERSION
except ImportError:
    VERSION = "dev"

try:
    LOCAL_SETTINGS
except NameError:
    try:
        from local_settings import *
    except ImportError:
        pass
