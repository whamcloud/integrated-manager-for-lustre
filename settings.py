# Django settings for hydra project.

try:
    import debug_toolbar
except:
    debug_toolbar = None

try:
    import django_extensions
except:
    django_extensions = None

import sys
import os
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'hydra',                 # Or path to database file if using sqlite3.
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
TIME_ZONE = None

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

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'pagination.middleware.PaginationMiddleware',
    'middleware.ExceptionPrinterMiddleware',
) + [('debug_toolbar.middleware.DebugToolbarMiddleware',), ()][debug_toolbar == None]


from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS +\
    ("django.core.context_processors.request",
     "hydracm.context_processors.page_load_time")

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
BROKER_USER = "hydra"
BROKER_PASSWORD = "hydra123"
BROKER_VHOST = "hydravhost"
CELERY_RESULT_BACKEND = "database"
CELERY_RESULT_DBURI = "mysql://root:@localhost/hydra"

# This is here because south is broken by something that happens when
# doing a 'python manage.py test': it creates databases using migrations,
# but then in between tests something removes all rows from all tables,
# including south's record of which migrations have been run, so when
# a subsequent test runs a 'syncdb', south tries to create tables
# which already exist.
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
    'pagination',
    'monitor',
    'configure',
    'hydraapi',
    'hydradashboard',
    'hydracm'
    ) + [('debug_toolbar',), ()][debug_toolbar == None] \
      + [('django_extensions',), ()][django_extensions == None]

INTERNAL_IPS = ('192.168.0.4',)


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
        },
        'django.db.backends': {
            'handlers': [],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

# Periods given in seconds
AUDIT_PERIOD = 10
JANITOR_PERIOD = 60
PLUGIN_DEFAULT_UPDATE_PERIOD = 5

JOB_MAX_AGE = 3600 * 24 * 7
AUDIT_MAX_AGE = 3600 * 24

SQL_RETRY_PERIOD = 10

# metrics settings
USE_FRONTLINE_METRICSTORE = True

CELERY_ROUTES = (
        {"monitor.tasks.audit_all": {"queue": "periodic"}},
        {"monitor.tasks.purge_and_optimize_metrics": {"queue": "periodic"}},
        {"monitor.tasks.drain_flms_table": {"queue": "periodic"}},
        {"monitor.tasks.parse_log_entries": {"queue": "parselog"}},
        {"configure.tasks.janitor": {"queue": "periodic"}},
        {"configure.tasks.set_state": {"queue": "serialize"}},
        {"configure.tasks.notify_state": {"queue": "serialize"}},
        {"configure.tasks.add_job": {"queue": "serialize"}},
        {"configure.tasks.complete_job": {"queue": "serialize"}},
        {"configure.tasks.run_job": {"queue": "jobs"}},
        {"monitor.tasks.test_host_contact": {"queue": "ssh"}},
        {"monitor.tasks.monitor_exec": {"queue": "ssh"}},
        )

CELERY_TRACK_STARTED = True
CELERY_DISABLE_RATE_LIMITS = True

# CELERY_ACKS_LATE is really important, it makes celery try a task again when a worker
# crashes (only works with proper AMQP backend like RabbitMQ, not DJKombu)
CELERY_ACKS_LATE = True

# Development defaults for log output
if DEBUG:
    LOG_PATH = ""
    JOB_LOG_PATH = "job.log"
    AUDIT_LOG_PATH = "audit.log"
    API_LOG_PATH = "hydraapi.log"
    SYSLOG_EVENTS_LOG_PATH = "syslog_events.log"
else:
    LOG_PATH = "/var/log/hydra"
    JOB_LOG_PATH = "/var/log/hydra/job.log"
    AUDIT_LOG_PATH = "/var/log/hydra/audit.log"
    API_LOG_PATH = "/var/log/hydra/hydraapi.log"
    SYSLOG_EVENTS_LOG_PATH = "/var/log/hydra/syslog_events.log"

_plugins_path = os.path.join(os.path.dirname(sys.modules['settings'].__file__), 'configure', 'plugins')
sys.path.append(_plugins_path)
INSTALLED_STORAGE_PLUGINS = ["linux"]

# Enable discovery-order assignment of LunNodes as 1st primary=true, 2nd use=true, subsequent use=false
PRIMARY_LUN_HACK = True

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
