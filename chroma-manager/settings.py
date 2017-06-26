# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import sys
import os
import socket
import logging

from scripts import nginx_settings

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

# We require python >= 2.6.5 for http://bugs.python.org/issue4978
if sys.version_info < (2, 6, 5):
    raise EnvironmentError("Python >= 2.6.5 is required")

DEBUG = True
TEMPLATE_DEBUG = DEBUG

populator = nginx_settings.get_dev_nginx_settings if DEBUG else nginx_settings.get_production_nginx_settings

for key, value in populator().items():
    setattr(sys.modules[__name__], key, value)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'chroma',                 # Or path to database file if using sqlite3.
        'USER': 'chroma',                  # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        'OPTIONS': {}
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

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

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

# A list of locations of additional static files
STATICFILES_DIRS = ()

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(rpb*-5f69cv=zc#$-bed7^_&8f)ve4dt4chacg$r^89)+%2i*'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    "django.core.context_processors.request",
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

AMQP_BROKER_USER = "chroma"
AMQP_BROKER_PASSWORD = "chroma123"
AMQP_BROKER_VHOST = "chromavhost"

BROKER_URL = "amqp://%s:%s@localhost:5672/%s" % (AMQP_BROKER_USER, AMQP_BROKER_PASSWORD, AMQP_BROKER_VHOST)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'south',
    'tastypie',
    'chroma_core',
    'chroma_api',
    'chroma_help',
    'benchmark'
)

OPTIONAL_APPS = ['django_extensions', 'django_coverage', 'django_nose', 'djsupervisor']
for app in OPTIONAL_APPS:
    import imp
    try:
        imp.find_module(app)
        INSTALLED_APPS = INSTALLED_APPS + (app,)
    except ImportError:
        pass

if 'django_nose' in INSTALLED_APPS:
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = ['--logging-filter=-south']

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'middleware.TastypieTransactionMiddleware',
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
PLUGIN_DEFAULT_UPDATE_PERIOD = 5

SQL_RETRY_PERIOD = 10

# Note: overriding the LUSTRE_MKFS_* settings will squash
# our own use of -I and -J for inode/journal size, so you
# must specify *all* the options you want, not just the ones
# you want to change.
LUSTRE_MKFS_OPTIONS_MDT = None
LUSTRE_MKFS_OPTIONS_OST = None
LUSTRE_MKFS_OPTIONS_MGS = None

# Argument to mkfs.ext4 '-J' option
JOURNAL_SIZE = "2048"

if DEBUG:
    LOG_PATH = ""
else:
    LOG_PATH = "/var/log/chroma"

if DEBUG:
    CRYPTO_FOLDER = "./"
else:
    CRYPTO_FOLDER = "/var/lib/chroma"

if DEBUG:
    GUNICORN_PID_PATH = "./gunicorn.pid"
else:
    GUNICORN_PID_PATH = "/var/run/gunicorn.pid"

LOG_LEVEL = logging.INFO

EMAIL_HOST = None
EMAIL_SUBJECT_PREFIX = "[Chroma Server]"
EMAIL_SENDER = "noreply@%s" % socket.getfqdn()

_plugins_path = os.path.join(os.path.dirname(sys.modules['settings'].__file__), 'chroma_core', 'plugins')
sys.path.append(_plugins_path)
INSTALLED_STORAGE_PLUGINS = ["linux", "linux_network"]
STORAGE_API_VERSION = 1

#: Whether to enable debug-level logging across chroma_core.lib.storage_plugin
STORAGE_PLUGIN_DEBUG = DEBUG
#: List of plugins to enable debug-level logging for
STORAGE_PLUGIN_DEBUG_PLUGINS = []

STORAGE_PLUGIN_ENABLE_STATS = True

# Control of the statistics storage
STATS_SIMPLE_WIPE = True                    # True means we simple delete everything that is older than the expiration, data not rolled up is lost.
STATS_10_SECOND_EXPIRATION = {'days': 1}    # Expiration must be multiple of 10 seconds.
STATS_1_MINUTE_EXPIRATION = {'days': 3}     # Expiration must be multiple of 1 minute.
STATS_5_MINUTE_EXPIRATION = {'days': 7}     # Expiration must be multiple of 5 minute.
STATS_1_HOUR_EXPIRATION = {'days': 30}      # Expiration must be multiple of 1 hour.
STATS_1_DAY_EXPIRATION = {'weeks': 10000}   # Expiration must be multiple of 1 day
STATS_FLUSH_RATE = 20                       # Flush 20 times per expiration interval - for 10 seconds sample flush every 1day/20.

# When agent sends VPD 0x80 and 0x83 serial numbers, which do we prefer to use
# for the canonical device serial on the manager?  Favorite first.
SERIAL_PREFERENCE = ['serial_83', 'serial_80']

# Use this to disable the manager's monitoring of your power control devices
# (eg, BMC, PDU outlets, etc.) This is necessary for sites where the manager
# server does not have access to the power control devices itself. However,
# IML will then *NO LONGER REPORT ANY FAILURE IN ANY POWER CONTROL DEVICES*.
# If power control becomes non-operational, automatic failover will not occur
# on failure, and manual intervention will be required to restore service to
# your file system. We recommend putting external monitoring in place if you
# disable this monitoring from the IML Manager.
DISABLE_POWER_CONTROL_DEVICE_MONITORING = False

# For django_coverage
COVERAGE_REPORT_HTML_OUTPUT_DIR = '/tmp/test_html'

# If you really want to point the Lustre servers at a specific NTP server
# NTP_SERVER_HOSTNAME = "myntpserver.mydoman"
NTP_SERVER_HOSTNAME = None

# Maximum latency between server and agent: used to
# check if clocks are 'reasonably' in sync
AGENT_CLOCK_TOLERANCE = 20

# Set to False to require logins even for read-only access
# to chroma_api
ALLOW_ANONYMOUS_READ = True

# Long poll timeout Seconds
LONG_POLL_TIMEOUT_SECONDS = (60 * 5)

# Allow Cookie to be read from JavaScript and passed to
# Realtime service
SESSION_COOKIE_HTTPONLY = False

# The value at which log entries in the database will be aged out to a
# flat text file in /var/log/chroma/db_log
DBLOG_HW = 1200000
# The value at which we stop aging database log entries out to a flat
# text file
DBLOG_LW = 1000000

# In development, where to serve repos from
DEV_REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.modules['settings'].__file__)), 'repo')

# If your storage servers will address the manager server by a non-default
# address or port, override this
SERVER_HTTP_URL = "https://%s:%s/" % (socket.getfqdn(), HTTPS_FRONTEND_PORT)

# Supported power control agents
SUPPORTED_FENCE_AGENTS = ['fence_apc', 'fence_apc_snmp', 'fence_ipmilan', 'fence_virsh']

# How long to wait for a storage server to reboot after installing a new kernel
INSTALLATION_REBOOT_TIMEOUT = 300

# How long to wait for an agent to resume contact after being restarted
AGENT_RESTART_TIMEOUT = 30

SSH_CONFIG = None

AUTH_PROFILE_MODULE = "chroma_core.UserProfile"

LOCAL_SETTINGS_FILE = "local_settings.py"

try:
    from scm_version import PACKAGE_VERSION, VERSION, IS_RELEASE, BUILD
except ImportError:
    PACKAGE_VERSION = '0.0.0'
    VERSION = 'dev'
    BUILD = 0
    IS_RELEASE = False

try:
    LOCAL_SETTINGS
except NameError:
    try:
        from local_settings import *
    except ImportError:
        pass
