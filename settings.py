# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import sys
import os
import socket
import logging

from scm_version import PACKAGE_VERSION, VERSION, IS_RELEASE, BUILD

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

# We require python >= 2.6.5 for http://bugs.python.org/issue4978
if sys.version_info < (2, 6, 5):
    raise EnvironmentError("Python >= 2.6.5 is required")

DEBUG = False

APP_PATH = "/usr/share/chroma-manager"

REPO_PATH = "/var/lib/chroma/repo"

REPORT_PATH = "/var/spool/iml/report"

HTTP_FRONTEND_PORT = 80

HTTPS_FRONTEND_PORT = os.getenv("HTTPS_FRONTEND_PORT", 443)

HTTP_AGENT_PORT = 8002

HTTP_AGENT2_PORT = 8003

PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")

HTTP_AGENT_PROXY_PASS = "http://{}:{}".format(PROXY_HOST, HTTP_AGENT_PORT)

HTTP_AGENT2_PROXY_PASS = "http://{}:{}".format(PROXY_HOST, HTTP_AGENT2_PORT)

HTTP_API_PORT = 8001

HTTP_API_PROXY_PASS = "http://{}:{}".format(PROXY_HOST, HTTP_API_PORT)

IML_API_PORT = 8004

IML_API_HOST = os.getenv("IML_API_HOST", PROXY_HOST)

IML_API_PROXY_PASS = "http://{}:{}".format(IML_API_HOST, IML_API_PORT)

WARP_DRIVE_PORT = 8890

WARP_DRIVE_PROXY_PASS = "http://{}:{}".format(PROXY_HOST, WARP_DRIVE_PORT)

MAILBOX_PORT = 8891

MAILBOX_PROXY_PASS = "http://{}:{}".format(PROXY_HOST, MAILBOX_PORT)

INFLUXDB_IML_DB = "iml"

INFLUXDB_STRATAGEM_SCAN_DB = "iml_stratagem_scans"

INFLUXDB_IML_STATS_DB = "iml_stats"

INFLUXDB_IML_STATS_LONG_DURATION = os.getenv("INFLUXDB_IML_STATS_LONG_DURATION", "52w")

INFLUXDB_SERVER_FQDN = os.getenv("INFLUXDB_SERVER_FQDN", PROXY_HOST)

INFLUXDB_PORT = 8086

INFLUXDB_PROXY_PASS = "http://{}:{}".format(INFLUXDB_SERVER_FQDN, INFLUXDB_PORT)

REPORT_PORT = 8893

REPORT_PROXY_PASS = "http://{}:{}".format(PROXY_HOST, REPORT_PORT)

SSL_PATH = "/var/lib/chroma"

DEVICE_AGGREGATOR_PORT = 8008

DEVICE_AGGREGATOR_PROXY_PASS = os.getenv(
    "DEVICE_AGGREGATOR_URL", "http://{}:{}".format(PROXY_HOST, DEVICE_AGGREGATOR_PORT)
)

ACTION_RUNNER_PORT = 8009

GRAFANA_PORT = 3000

GRAFANA_PROXY_PASS = "http://{}:{}".format(PROXY_HOST, GRAFANA_PORT)

TIMER_PORT = 8892

TIMER_SERVER_FQDN = os.getenv("TIMER_SERVER_FQDN", PROXY_HOST)

TIMER_PROXY_PASS = "http://{}:{}".format(TIMER_SERVER_FQDN, TIMER_PORT)

BRANDING = os.getenv("BRANDING", "Whamcloud")

EXA_VERSION = os.getenv("EXA_VERSION")

USE_STRATAGEM = os.getenv("USE_STRATAGEM", "false")

ALLOWED_HOSTS = ["*"]

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        "NAME": "chroma",  # Or path to database file if using sqlite3.
        "USER": "chroma",  # Not used with sqlite3.
        "PASSWORD": os.getenv("DB_PASSWORD", ""),  # Not used with sqlite3.
        "HOST": os.getenv("DB_HOST", ""),  # Set to empty string for localhost. Not used with sqlite3.
        "PORT": os.getenv("DB_PORT", ""),  # Set to empty string for default. Not used with sqlite3.
        "OPTIONS": {},
        "ATOMIC_REQUESTS": False,
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
LANGUAGE_CODE = "en-us"

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
MEDIA_ROOT = ""

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ""

# Absolute path to the directory that holds static files.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(SITE_ROOT, "static")

# URL that handles the static files served from STATIC_ROOT.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = "/static/"

# A list of locations of additional static files
STATICFILES_DIRS = ()

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = "(rpb*-5f69cv=zc#$-bed7^_&8f)ve4dt4chacg$r^89)+%2i*"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.tz",
            ],
        },
    }
]

ROOT_URLCONF = "urls"

AMQP_BROKER_USER = "chroma"
AMQP_BROKER_PASSWORD = "chroma123"
AMQP_BROKER_VHOST = "chromavhost"
AMQP_BROKER_HOST = os.getenv("AMQP_BROKER_HOST", "localhost")
AMQP_BROKER_PORT = "5672"

BROKER_URL = "amqp://{}:{}@{}:{}/{}".format(
    AMQP_BROKER_USER, AMQP_BROKER_PASSWORD, AMQP_BROKER_HOST, AMQP_BROKER_PORT, AMQP_BROKER_VHOST
)

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "tastypie",
    "chroma_core.app.ChromaCoreAppConfig",
    "chroma_api",
    "chroma_help",
)

OPTIONAL_APPS = ["django_coverage", "django_nose"]
for app in OPTIONAL_APPS:
    import imp

    try:
        imp.find_module(app)
        INSTALLED_APPS = INSTALLED_APPS + (app,)
    except ImportError:
        pass

if "django_nose" in INSTALLED_APPS:
    TEST_RUNNER = "django_nose.NoseTestSuiteRunner"
    NOSE_ARGS = []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


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

LOG_PATH = os.getenv("LOG_PATH", "/var/log/chroma")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "formatters": {
        "django.server": {"()": "django.utils.log.ServerFormatter", "format": "[%(server_time)s] %(message)s"}
    },
    "handlers": {
        "console": {"level": "INFO", "filters": ["require_debug_true"], "class": "logging.StreamHandler"},
        "console_debug_false": {"level": "ERROR", "filters": ["require_debug_false"], "class": "logging.StreamHandler"},
        "django.server": {"level": "INFO", "class": "logging.StreamHandler", "formatter": "django.server"},
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {"handlers": ["console", "console_debug_false", "mail_admins"], "level": "INFO"},
        "django.server": {"handlers": ["django.server"], "level": "INFO", "propagate": False},
    },
}

CRYPTO_FOLDER = "/var/lib/chroma"

GUNICORN_PID_PATH = "/var/run/gunicorn.pid"

LOG_LEVEL = int(os.getenv("LOG_LEVEL", logging.INFO))

EMAIL_HOST = None
EMAIL_SUBJECT_PREFIX = "[Chroma Server]"
EMAIL_SENDER = "noreply@%s" % socket.getfqdn()

_plugins_path = os.path.join(os.path.dirname(sys.modules["settings"].__file__), "chroma_core", "plugins")
sys.path.append(_plugins_path)
INSTALLED_STORAGE_PLUGINS = ["linux", "linux_network"]
STORAGE_API_VERSION = 1

#: Whether to enable debug-level logging across chroma_core.lib.storage_plugin
STORAGE_PLUGIN_DEBUG = DEBUG
#: List of plugins to enable debug-level logging for
STORAGE_PLUGIN_DEBUG_PLUGINS = []

# When agent sends VPD 0x80 and 0x83 serial numbers, which do we prefer to use
# for the canonical device serial on the manager?  Favorite first.
SERIAL_PREFERENCE = ["serial_83", "serial_80"]

# For django_coverage
COVERAGE_REPORT_HTML_OUTPUT_DIR = "/tmp/test_html"

# If you really want to point the Lustre servers at a specific NTP server
# NTP_SERVER_HOSTNAME = "myntpserver.mydoman"
NTP_SERVER_HOSTNAME = os.getenv("NTP_SERVER_HOSTNAME", None)

# Maximum latency between server and agent: used to
# check if clocks are 'reasonably' in sync
AGENT_CLOCK_TOLERANCE = 20

# Set to False to require logins even for read-only access
# to chroma_api
ALLOW_ANONYMOUS_READ = True

# Long poll timeout Seconds
LONG_POLL_TIMEOUT_SECONDS = 60 * 5

# Allow Cookie to be read from JavaScript and passed to
# Realtime service
SESSION_COOKIE_HTTPONLY = False

# The value at which log entries in the database will be aged out to a
# flat text file in /var/log/chroma/db_log
DBLOG_HW = int(os.getenv("DBLOG_HW", 1200000))
# The value at which we stop aging database log entries out to a flat
# text file
DBLOG_LW = int(os.getenv("DBLOG_LW", 1000000))

# In development, where to serve repos from
DEV_REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.modules["settings"].__file__)), "repo")

SERVER_FQDN = os.getenv("SERVER_FQDN", socket.getfqdn())

# If your storage servers will address the manager server by a non-default
# address or port, override this
SERVER_HTTP_URL = "https://%s:%s" % (SERVER_FQDN, HTTPS_FRONTEND_PORT)

# How long to wait for a storage server to reboot after installing a new kernel
INSTALLATION_REBOOT_TIMEOUT = 300

# How long to wait for an agent to resume contact after being restarted
AGENT_RESTART_TIMEOUT = 30

SSH_CONFIG = None

TASTYPIE_DEFAULT_FORMATS = ["json"]

SILENCED_SYSTEM_CHECKS = ["contenttypes.E001", "contenttypes.E002"]


LOCAL_SETTINGS_FILE = "local_settings.py"

try:
    from local_settings import *
except ImportError:
    pass
