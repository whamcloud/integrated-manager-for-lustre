# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import hashlib
import logging
import getpass
import socket
import sys
import xmlrpclib
import time
import os
import json
import glob
import shutil

# without GNU readline, raw_input prompt goes to stderr
import readline

assert readline

from collections import namedtuple

from chroma_core.lib.util import chroma_settings

settings = chroma_settings()

from django.contrib.auth.models import User, Group
from django.core.management import ManagementUtility
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from tastypie.models import ApiKey

from kombu.connection import BrokerConnection
from chroma_core.models.bundle import Bundle
from chroma_core.services.crypto import Crypto
from chroma_core.models import ServerProfile, ServerProfilePackage, ServerProfileValidation
from chroma_core.lib.util import CommandLine, CommandError
from iml_common.lib.ntp import NTPConfig
from iml_common.lib.firewall_control import FirewallControl
from iml_common.lib.service_control import ServiceControl, ServiceControlEL7

log = logging.getLogger("installation")
try:
    # python2.7
    log.addHandler(logging.StreamHandler(stream=sys.stdout))
except TypeError:
    # python2.6
    log.addHandler(logging.StreamHandler(strm=sys.stdout))
log.setLevel(logging.INFO)

firewall_control = FirewallControl.create()


class ServiceConfig(CommandLine):
    REQUIRED_DB_SPACE_GB = 100
    bytes_in_gigabytes = 1073741824

    def __init__(self):
        self.verbose = False

    @staticmethod
    def _check_name_resolution():
        """
        Check:
         * that the hostname is not localhost
         * that the FQDN can be looked up from hostname
         * that an IP can be looked up from the hostname

        This check is done ahead of configuring RabbitMQ, which fails unobviously if the
        name resolution is bad.

        :return: True if OK, else False

        """
        try:
            hostname = socket.gethostname()
        except socket.error:
            log.error("Error: Unable to get the servers hostname. " "Please correct the hostname esolution.")
            return False

        if hostname == "localhost":
            log.error(
                "Error: Currently the hostname is '%s' which is invalid. " "Please correct the hostname resolution.",
                hostname,
            )
            return False

        try:
            fqdn = socket.getfqdn(hostname)
        except socket.error:
            log.error(
                "Error: Unable to get the FQDN for the server name '%s'. " "Please correct the hostname resolution.",
                hostname,
            )
            return False
        else:
            if fqdn == "localhost.localdomain":
                log.error("Error: FQDN resolves to localhost.localdomain")
                return False

        try:
            socket.gethostbyname(hostname)
        except socket.error:
            log.error(
                "Error: Unable to get the ip address for the server name '%s'. "
                "Please correct the hostname resolution.",
                hostname,
            )
            return False

        return True

    @staticmethod
    def _db_accessible():
        """Discover whether we have a working connection to the database"""
        from psycopg2 import OperationalError
        from django.db import connection

        try:
            connection.introspection.table_names()
            return True
        except OperationalError:
            connection._rollback()
            return False

    def print_usage_message(self):
        rc, out, err = self.try_shell(["man", "-P", "cat", "chroma-config"])

        return out

    def _db_populated(self):
        """Discover whether the database has this application's tables"""
        from django.db.utils import DatabaseError

        if not self._db_accessible():
            return False
        try:
            from south.models import MigrationHistory

            MigrationHistory.objects.count()
            return True
        except DatabaseError:
            from django.db import connection

            connection._rollback()
            return False

    def _db_current(self):
        """Discover whether there are any outstanding migrations to be
           applied"""
        if not self._db_populated():
            return False

        from south.models import MigrationHistory

        applied_migrations = MigrationHistory.objects.all().values("app_name", "migration")
        applied_migrations = [(mh["app_name"], mh["migration"]) for mh in applied_migrations]

        from south import migration

        for app_migrations in list(migration.all_migrations()):
            for m in app_migrations:
                if (m.app_label(), m.name()) not in applied_migrations:
                    return False
        return True

    def _users_exist(self):
        """Discover whether any users exist in the database"""
        if not self._db_populated():
            return False

        return bool(User.objects.count() > 0)

    def configured(self):
        """Return True if the system has been configured far enough to present
        a user interface"""
        return self._db_current() and self._users_exist() and self._rabbit_configured()

    def _setup_ntp(self, server):
        """
        Change the ntp configuration file to use the server passed.

        If no server is passed then use the existing setting and if there is no existing setting ask the user
        which server they would like to use.

        Enable NTPConfig to recognise legacy line marker used in previous IML manager NTP configurations routines by
        passing it as a parameter to the get_configured_server method call
        """
        ntp = NTPConfig(logger=log)
        existing_server = ntp.get_configured_server(markers=["# Added by chroma-manager\n"])

        if not server:
            if existing_server:
                server = existing_server
                log.info("Using existing (chroma configured) ntp server: %s" % existing_server)
            else:
                # Only if you haven't already set it
                server = self.get_input(msg="NTP Server", default="localhost")

        log.info("Writing ntp configuration: %s " % server)

        error = ntp.add(server)
        if error:
            log.error("Failed to write ntp server (%s) to config file (%s), %s" % (server, ntp.CONFIG_FILE, error))
            raise RuntimeError("Failure when writing ntp config: %s" % error)

        if ServiceControl.create("firewalld").running:
            error = firewall_control.add_rule("123", "udp", "ntpd")

            if error:
                log.error("firewall command failed:\n%s" % error)
                raise RuntimeError("Failure when opening port in firewall for ntpd: %s" % error)

        log.info("Restarting ntp")
        ntp_service = ServiceControl.create("ntpd")

        error = ntp_service.restart()
        if error:
            log.error(error)
            raise RuntimeError(error)

        ntp_service.enable()

    def _rabbit_configured(self):
        # Data message should be forwarded to AMQP
        try:
            with BrokerConnection(settings.BROKER_URL) as conn:
                c = conn.connect()
                return c.connected
        except socket.error:
            return False

    def _setup_rabbitmq_service(self):
        log.info("Starting RabbitMQ...")
        # special case where service requires legacy service control
        rabbit_service = ServiceControlEL7("rabbitmq-server")

        error = rabbit_service.enable()
        if error:
            log.error(error)
            raise RuntimeError(error)

        error = rabbit_service._stop()
        if error:
            log.error(error)
            raise RuntimeError(error)
        error = rabbit_service._start()
        if error:
            log.error(error)
            raise RuntimeError(error)

    def _setup_rabbitmq_credentials(self):
        # Enable use from dev_setup as a nonroot user on linux
        sudo = []
        if "linux" in sys.platform and os.geteuid() != 0:
            sudo = ["sudo"]

        self.try_shell(sudo + ["rabbitmqctl", "stop_app"])
        self.try_shell(sudo + ["rabbitmqctl", "reset"])
        self.try_shell(sudo + ["rabbitmqctl", "start_app"])

        log.info("Creating RabbitMQ user...")
        self.try_shell(sudo + ["rabbitmqctl", "add_user", settings.AMQP_BROKER_USER, settings.AMQP_BROKER_PASSWORD])

        log.info("Creating RabbitMQ vhost...")
        self.try_shell(sudo + ["rabbitmqctl", "add_vhost", settings.AMQP_BROKER_VHOST])

        self.try_shell(
            sudo
            + [
                "rabbitmqctl",
                "set_permissions",
                "-p",
                settings.AMQP_BROKER_VHOST,
                settings.AMQP_BROKER_USER,
                ".*",
                ".*",
                ".*",
            ]
        )

        # Enable use of the management plugin if its available, else this tag is just ignored.
        self.try_shell(sudo + ["rabbitmqctl", "set_user_tags", settings.AMQP_BROKER_USER, "management"])

    def _setup_crypto(self):
        if not os.path.exists(settings.CRYPTO_FOLDER):
            os.makedirs(settings.CRYPTO_FOLDER)

        # FIXME: tidy up Crypto, some of its methods are no longer used
        crypto = Crypto()
        # The server_cert attribute is created on read
        crypto.server_cert

    CONTROLLED_SERVICES = ["iml-manager.target", "nginx"]

    MANAGER_SERVICES = [
        "iml-corosync.service",
        "iml-gunicorn.service",
        "iml-http-agent.service",
        "iml-job-scheduler.service",
        "iml-lustre-audit.service",
        "iml-plugin-runner.service",
        "iml-power-control.service",
        "iml-syslog.service",
        "iml-stats.service",
        "iml-view-server.service",
        "iml-realtime.service",
        "device-aggregator.socket",
        "iml-srcmap-reverse.socket",
    ]

    def _enable_services(self):
        log.info("Enabling daemons")

        xs = self.CONTROLLED_SERVICES + self.MANAGER_SERVICES

        for service in xs:
            controller = ServiceControl.create(service)

            error = controller.enable()
            if error:
                log.error(error)
                raise RuntimeError(error)

    def _start_services(self):
        log.info("Starting daemons")
        for service in self.CONTROLLED_SERVICES:
            controller = ServiceControl.create(service)

            if controller.running:
                if service.endswith(".target"):
                    error = False
                else:
                    error = controller.reload()
            else:
                error = controller.start()
            if error:
                log.error(error)
                raise RuntimeError(error)

    def _stop_services(self):
        log.info("Stopping daemons")
        for service in self.CONTROLLED_SERVICES:
            controller = ServiceControl.create(service)

            error = controller.stop()
            if error:
                log.error(error)
                raise RuntimeError(error)

    def _init_pgsql(self, database):
        rc, out, err = self.shell(["service", "postgresql", "initdb"])
        if rc != 0:
            if "is not empty" not in out:
                log.error("Failed to initialize postgresql service")
                log.error("stdout:\n%s" % out)
                log.error("stderr:\n%s" % err)
                raise CommandError("service postgresql initdb", rc, out, err)
            return
        # Only mess with auth if we've freshly initialized the db
        self._config_pgsql_auth(database)

    @staticmethod
    def _config_pgsql_auth(database):
        auth_cfg_file = "/var/lib/pgsql/data/pg_hba.conf"
        os.rename(auth_cfg_file, "%s.dist" % auth_cfg_file)
        with open(auth_cfg_file, "w") as cfg:
            # Allow our django user to connect with no password
            cfg.write("local\tall\t%s\t\ttrust\n" % database["USER"])
            # Allow the system superuser (postgres) to connect
            cfg.write("local\tall\tall\t\tident\n")

    PathStats = namedtuple("PathStats", ["total", "used", "free"])

    def _path_space(self, path):
        """Returns the disk statistics of the given path.

        Returned values is a named tuple with attributes 'total', 'used' and
        'free', which are the amount of total, used and free space, in bytes.
        """
        statvfs = os.statvfs(path)
        total = statvfs.f_frsize * statvfs.f_blocks  # size in bytes
        free_space = statvfs.f_frsize * statvfs.f_bfree  # number of free bytes
        used = total - free_space  # number of used bytes

        return self.PathStats(total, used, free_space)

    def _check_db_space(self, required_space_gigabytes):
        rc, out, err = self.try_shell(["su", "postgres", "-c", "psql -c 'SHOW data_directory;'"])
        db_storage_path = out.split()[2]
        stats = self._path_space(db_storage_path)
        gigabytes_free = stats.free / self.bytes_in_gigabytes

        if gigabytes_free < required_space_gigabytes:
            error_msg = (
                "Insufficient space for postgres database in path directory %s. %sGB available, %sGB required "
                % (db_storage_path, gigabytes_free, required_space_gigabytes)
            )
            log.error(error_msg)
            return error_msg

    def _setup_pgsql(self, database, check_db_space):
        log.info("Setting up PostgreSQL service...")

        self._init_pgsql(database)

        postgresql_service = ServiceControl.create("postgresql")
        postgresql_service.restart()
        postgresql_service.enable()

        tries = 0
        while self.shell(["su", "postgres", "-c", "psql -c '\\d'"])[0] != 0:
            if tries >= 4:
                raise RuntimeError("Timed out waiting for PostgreSQL service to start")
            tries += 1
            time.sleep(1)

        error = self._check_db_space(self.REQUIRED_DB_SPACE_GB)

        if check_db_space and error:
            return error

        if not self._db_accessible():
            log.info("Creating database owner '%s'...\n" % database["USER"])

            # Enumerate existing roles
            _, roles_str, _ = self.try_shell(["su", "postgres", "-c", "psql -t -c 'select " "rolname from pg_roles;'"])
            roles = [line.strip() for line in roles_str.split("\n") if line.strip()]

            # Create database['USER'] role if not found
            if not database["USER"] in roles:
                self.try_shell(
                    [
                        "su",
                        "postgres",
                        "-c",
                        "psql -c 'CREATE ROLE %s NOSUPERUSER "
                        "CREATEDB NOCREATEROLE INHERIT LOGIN;'" % database["USER"],
                    ]
                )

            log.info("Creating database '%s'...\n" % database["NAME"])
            self.try_shell(["su", "postgres", "-c", "createdb -O %s %s;" % (database["USER"], database["NAME"])])
        return None

    @staticmethod
    def get_input(msg, empty_allowed=True, password=False, default=""):
        if msg == "":
            raise RuntimeError("Calling get_input, msg must not be empty")

        if default != "":
            msg = "%s [%s]" % (msg, default)

        msg = "%s: " % msg

        answer = ""
        while answer == "":
            if password:
                answer = getpass.getpass(msg)
            else:
                answer = raw_input(msg)

            if answer == "":
                if not empty_allowed:
                    print("A value is required")
                    continue
                if default != "":
                    answer = default
                break

        return answer

    def get_pass(self, msg="", empty_allowed=True, confirm_msg=""):
        while True:
            pass1 = self.get_input(msg=msg, empty_allowed=empty_allowed, password=True)

            pass2 = self.get_input(msg=confirm_msg, empty_allowed=empty_allowed, password=True)

            if pass1 != pass2:
                print("Passwords do not match!")
            else:
                return pass1

    @staticmethod
    def validate_email(email):
        try:
            validate_email(email)
        except ValidationError:
            return False
        return True

    def _user_account_prompt(self):
        log.info("An administrative user account will now be created using the " + "credentials which you provide.")

        valid_username = False
        while not valid_username:
            username = self.get_input(msg="Username", empty_allowed=False)
            if username.find(" ") > -1:
                print("Username cannot contain spaces")
                continue
            valid_username = True

        password = self.get_pass(msg="Password", empty_allowed=False, confirm_msg="Confirm password")

        valid_email = False
        while not valid_email:
            email = self.get_input(msg="Email")
            if email and not self.validate_email(email):
                print("Email is not valid")
                continue
            valid_email = True

        return username, email, password

    def _syncdb(self):
        if not self._db_current():
            log.info("Creating database tables...")
            args = ["", "syncdb", "--noinput", "--migrate"]
            if not self.verbose:
                args = args + ["--verbosity", "0"]
            ManagementUtility(args).execute()
        else:
            log.info("Database tables already OK")

    def _setup_database(self, check_db_space):
        error = None
        if not self._db_accessible():
            # For the moment use the builtin configuration
            # TODO: this is where we would establish DB name and credentials
            databases = settings.DATABASES

            error = self._setup_pgsql(databases["default"], check_db_space)
        else:
            log.info("DB already accessible")

        if error:
            return error

        self._syncdb()

    def _populate_database(self, username, password):
        if not self._users_exist():
            if not username:
                username, email, password = self._user_account_prompt()
            else:
                email = ""
            user = User.objects.create_superuser(username, email, password)
            user.groups.add(Group.objects.get(name="superusers"))
            log.info("User '%s' successfully created." % username)
        else:
            log.info("User accounts already created")

        API_USERNAME = "api"

        try:
            User.objects.get(username=API_USERNAME)
            log.info("API user already created")
        except User.DoesNotExist:
            api_user = User.objects.create_superuser(API_USERNAME, "", User.objects.make_random_password())
            api_user.groups.add(Group.objects.get(name="superusers"))
            ApiKey.objects.get_or_create(user=api_user)
            log.info("API user created")

        return

    def _configure_selinux(self):
        try:
            self.try_shell(["sestatus | grep enabled"], shell=True)
        except CommandError:
            return

        # This is required for opening connections between
        # nginx and rabbitmq-server
        self.try_shell(["setsebool -P httpd_can_network_connect 1"], shell=True)

        # This is required because of bad behaviour in python's 'uuid'
        # module (see HYD-1475)
        self.try_shell(["setsebool -P httpd_tmp_exec 1"], shell=True)

    def _configure_firewall(self):
        if ServiceControl.create("firewalld").running:
            for port in [80, 443]:
                self.try_shell(["firewall-cmd", "--permanent", "--add-port={}/tcp".format(port)])
                self.try_shell(["firewall-cmd", "--add-port={}/tcp".format(port)])

    def set_nginx_config(self):
        project_dir = os.path.dirname(os.path.realpath(settings.__file__))
        conf_template = os.path.join(project_dir, "chroma-manager.conf.template")

        nginx_settings = [
            "REPO_PATH",
            "HTTP_FRONTEND_PORT",
            "HTTPS_FRONTEND_PORT",
            "HTTP_AGENT_PROXY_PASS",
            "HTTP_API_PROXY_PASS",
            "REALTIME_PROXY_PASS",
            "VIEW_SERVER_PROXY_PASS",
            "SSL_PATH",
            "DEVICE_AGGREGATOR_PORT",
            "UPDATE_HANDLER_PROXY_PASS",
            "DEVICE_AGGREGATOR_PROXY_PASS",
            "SRCMAP_REVERSE_PROXY_PASS",
        ]

        with open(conf_template, "r") as f:
            config = f.read()
            for setting in nginx_settings:
                config = config.replace("{{%s}}" % setting, str(getattr(settings, setting)))

            with open("/etc/nginx/conf.d/chroma-manager.conf", "w") as f2:
                f2.write(config)

    def _create_fake_bundle(self):
        EXTERNAL_BUNDLE_DIR = "/var/lib/chroma/repo/external/7/"

        if not os.path.exists(EXTERNAL_BUNDLE_DIR):
            os.makedirs(EXTERNAL_BUNDLE_DIR)

        FAKE_BUNDLE = '{"description": "fake bundle as a placeholder for externally available packages", "distro_version": "7", "filename": "", "version": "0.0.0", "distro": "el7", "name": "external"}'

        with open(os.path.join(EXTERNAL_BUNDLE_DIR, "meta"), "w") as f:
            f.write(FAKE_BUNDLE)

        bundle("register", EXTERNAL_BUNDLE_DIR)

    def _register_profiles(self):
        for x in glob.glob("/usr/share/chroma-manager/*.profile"):
            print("Registering profile: {}".format(x))
            with open(x) as f:
                register_profile(f)

    def container_setup(self, username, password):
        self._syncdb()
        self._create_fake_bundle()
        self._register_profiles()

        self._populate_database(username, password)

        self._setup_crypto()

        # Many iml docker containers depend on the iml-settings file and its contents. However, redirecting the settings output
        # into /var/lib/chroma/iml-settings.conf is not sufficient as the > operator is not atomic (the file will be created without content).
        # The mv command is atomic, thus the contents will be created in a temp file and then moved into /var/lib/chroma/iml-settings.conf.
        f = open("/tmp/temp-settings.conf", "w")
        self.try_shell(["python", "./manage.py", "print-settings"], mystdout=f)
        shutil.move("/tmp/temp-settings.conf", "/var/lib/chroma/iml-settings.conf")

    def setup(self, username, password, ntp_server, check_db_space):
        if not self._check_name_resolution():
            return ["Name resolution is not correctly configured"]

        self._configure_selinux()
        self._configure_firewall()

        self.set_nginx_config()

        error = self._setup_database(check_db_space)
        if check_db_space and error:
            return [error]

        self._create_fake_bundle()
        self._register_profiles()

        self._populate_database(username, password)

        self._setup_ntp(ntp_server)
        self._setup_crypto()

        self._setup_rabbitmq_service()
        self._setup_rabbitmq_credentials()

        self._enable_services()
        self._start_services()

        return self.validate()

    def start(self):
        if not self._db_current():
            log.error("Cannot start, database not configured")
            return
        self._start_services()

    def stop(self):
        self._stop_services()

    @staticmethod
    def _service_config(interesting_services=None):
        """Interrogate the current status of services, it should be noted that el7 calls to
        systemctl through ServiceControl will redirect to chkconfig if the specified service is
        not native (SysV style init as opposed to systemd unit init file)
        """
        log.info("Checking service configuration...")

        services = {}
        for service_name in interesting_services:
            controller = ServiceControl.create(service_name)
            services[service_name] = {"enabled": controller.enabled, "running": controller.running}

        return services

    def validate(self):
        errors = []
        if not self._db_accessible():
            errors.append("Cannot connect to database")
        elif not self._db_current():
            errors.append("Database tables out of date")
        elif not self._users_exist():
            errors.append("No user accounts exist")

        # Check services are active
        interesting_services = self.MANAGER_SERVICES + self.CONTROLLED_SERVICES + ["postgresql", "rabbitmq-server"]

        service_config = self._service_config(interesting_services)
        for s in interesting_services:
            try:
                service_status = service_config[s]
                if not service_status["enabled"]:
                    errors.append("Service %s not set to start at boot" % s)
                if not service_status["running"]:
                    errors.append("Service %s is not running" % s)
            except KeyError:
                errors.append("Service %s not found" % s)

        return errors

    @staticmethod
    def _write_local_settings(databases):
        # Build a local_settings file
        project_dir = os.path.dirname(os.path.realpath(settings.__file__))
        local_settings = os.path.join(project_dir, settings.LOCAL_SETTINGS_FILE)
        local_settings_str = ""

        # Usefully, a JSON dict looks a lot like python
        local_settings_str += "DATABASES = %s\n" % json.dumps(databases, indent=4).replace("null", "None")

        # Dump local_settings_str to local_settings
        open(local_settings, "w").write(local_settings_str)

        # TODO: support SERVER_HTTP_URL


def bundle(operation, path=None):
    if operation == "register":
        # Create or update a bundle record
        meta_path = os.path.join(path, "meta")
        try:
            meta = json.load(open(meta_path))
        except (IOError, ValueError):
            raise RuntimeError("Could not read bundle metadata from %s" % meta_path)

        log.debug("Loaded bundle meta for %s from %s" % (meta["name"], meta_path))

        # Bundle version is optional, defaults to "0.0.0"
        version = meta.get("version", "0.0.0")
        if Bundle.objects.filter(bundle_name=meta["name"]).exists():
            log.debug("Updating bundle %s" % meta["name"])
            Bundle.objects.filter(bundle_name=meta["name"]).update(
                version=version, location=path, description=meta["description"]
            )
        else:
            log.debug("Creating bundle %s" % meta["name"])
            Bundle.objects.create(
                bundle_name=meta["name"], version=version, location=path, description=meta["description"]
            )
    elif operation == "delete":
        # remove bundle record
        try:
            bundle = Bundle.objects.get(location=path)
            bundle.delete()
        except Bundle.DoesNotExist:
            # doesn't exist anyway, so just exit silently
            return
    else:
        raise RuntimeError("Received unknown bundle operation '%s'" % operation)


def register_profile(profile_file):
    default_profile = {
        "ui_name": "Default Profile",
        "managed": False,
        "worker": False,
        "name": "default",
        "bundles": [],
        "ui_description": "This is the hard coded default profile.",
        "user_selectable": True,
        "initial_state": "monitored",
        "packages": {},
        "validation": [],
        "ntp": False,
        "corosync": False,
        "corosync2": False,
        "pacemaker": False,
    }

    # create new profile record
    try:
        data = json.load(profile_file)
    except ValueError as e:
        raise RuntimeError("Profile %s is malformed: %s" % (profile_file.name, e.message))

    log.debug("Loaded profile '%s' from %s" % (data["name"], profile_file))

    # Validate: check all referenced bundles exist
    validate_bundles = set(data["bundles"])
    missing_bundles = []
    for bundle_name in validate_bundles:
        if not Bundle.objects.filter(bundle_name=bundle_name).exists():
            missing_bundles.append(bundle_name)

    # Make sure new keys have a default value set.
    for key in data.keys():
        assert key in default_profile, "Key %s is not in the default profile" % key

    # Take the default and replace the values that are in the data
    data = dict(default_profile.items() + data.items())

    if missing_bundles:
        log.error("Bundles not found for profile '%s': %s" % (data["name"], ", ".join(missing_bundles)))
        sys.exit(-1)

    calculated_profile_fields = set(["packages", "name", "bundles", "validation"])
    regular_profile_fields = set(data.keys()) - calculated_profile_fields

    try:
        profile = ServerProfile.objects.get(name=data["name"])
        log.debug("Updating profile %s" % data["name"])
        for field in regular_profile_fields:
            setattr(profile, field, data[field])
        profile.save()
    except ServerProfile.DoesNotExist:
        log.debug("Creating profile %s" % data["name"])
        kwargs = dict([(f, data[f]) for f in regular_profile_fields])
        kwargs["name"] = data["name"]
        profile = ServerProfile.objects.create(**kwargs)

    for name in data["bundles"]:
        profile.bundles.add(Bundle.objects.get(bundle_name=name))

    for bundle_name, package_list in data["packages"].items():
        for package_name in package_list:
            ServerProfilePackage.objects.get_or_create(
                server_profile=profile, bundle=Bundle.objects.get(bundle_name=bundle_name), package_name=package_name
            )

    profile.serverprofilevalidation_set.all().delete()
    for validation in data["validation"]:
        profile.serverprofilevalidation_set.add(ServerProfileValidation(**validation))


def delete_profile(name):
    # remove profile record
    try:
        profile = ServerProfile.objects.get(name=name)
        profile.delete()
    except ServerProfile.DoesNotExist:
        # doesn't exist anyway, so just exit silently
        return


def default_profile(name):
    """
    Set the default flag on the named profile and clear the default
    flag on all other profiles.

    :param name: A server profile name
    :return: None
    """
    try:
        ServerProfile.objects.get(name=name)
    except ServerProfile.DoesNotExist:
        log.error("Profile '%s' not found" % name)
        sys.exit(-1)

    ServerProfile.objects.update(default=False)
    ServerProfile.objects.filter(name=name).update(default=True)


def chroma_config():
    """Entry point for chroma-config command line tool.

    Distinction between this and ServiceConfig is that CLI-specific stuff lives here:
    ServiceConfig utility methods don't do sys.exit or parse arguments.

    """
    service_config = ServiceConfig()

    try:
        command = sys.argv[1]
    except IndexError:
        log.error("%s" % service_config.print_usage_message())
        sys.exit(-1)

    if command in ("stop", "start", "restart") and os.geteuid():
        log.error("You must be root to run this command.")
        sys.exit(-1)

    if command in ("-h", "--help"):
        log.info("%s" % service_config.print_usage_message())

    def print_errors(errors):
        if errors:
            log.error("Errors found:")
            for error in errors:
                log.error("  * %s" % error)
        else:
            log.info("OK.")

    if "-v" in sys.argv:
        service_config.verbose = True
        sys.argv.remove("-v")

    if command == "setup":

        def usage():
            log.error("Usage: setup [-v] [username password ntpserver]")
            sys.exit(-1)

        if "--no-dbspace-check" in sys.argv:
            check_db_space = False
            sys.argv.remove("--no-dbspace-check")
        else:
            check_db_space = True

        if len(sys.argv) == 2:
            username = None
            password = None
            ntpserver = None

        elif len(sys.argv) == 5:
            username = sys.argv[2]
            password = sys.argv[3]
            ntpserver = sys.argv[4]

        else:
            usage()

        log.info("Starting setup...\n")
        errors = service_config.setup(username, password, ntpserver, check_db_space)
        if errors:
            print_errors(errors)
            sys.exit(-1)
        else:
            log.info("\nSetup complete.")
            sys.exit(0)
    elif command == "container-setup":

        def usage():
            log.error("Usage: container-setup [username password]")
            sys.exit(-1)

        if len(sys.argv) == 2:
            username = None
            password = None
        elif len(sys.argv) == 4:
            username = sys.argv[2]
            password = sys.argv[3]
        else:
            usage()

        log.info("Starting container setup...\n")
        errors = service_config.container_setup(username, password)

        if errors:
            print_errors(errors)
            sys.exit(-1)
        else:
            log.info("\nContainer setup complete.")
            sys.exit(0)
    elif command == "dbsetup":
        if "--no-dbspace-check" in sys.argv:
            check_db_space = False
            sys.argv.remove("--no-dbspace-check")
        else:
            check_db_space = True

        service_config._setup_database(check_db_space)
    elif command == "validate":
        errors = service_config.validate()
        print_errors(errors)
        if errors:
            sys.exit(1)
        else:
            sys.exit(0)
    elif command == "stop":
        service_config.stop()
    elif command == "start":
        service_config.start()
    elif command == "restart":
        service_config.stop()
        service_config.start()
    elif command == "bundle":
        operation = sys.argv[2]
        bundle(operation, path=sys.argv[3])
    elif command == "profile":
        operation = sys.argv[2]
        if operation == "register":
            try:
                register_profile(open(sys.argv[3]))
            except IOError:
                print("Error opening %s" % sys.argv[3])
                sys.exit(-1)
        elif operation == "delete":
            delete_profile(sys.argv[3])
        elif operation == "default":
            default_profile(sys.argv[3])
        else:
            raise NotImplementedError(operation)
    else:
        log.error("Invalid command '%s'" % command)
        sys.exit(-1)
