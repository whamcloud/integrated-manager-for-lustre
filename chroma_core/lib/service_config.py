

import logging
import subprocess
import getpass

log = logging.getLogger('installation')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)

import settings
from django.contrib.auth.models import User, Group
from django.core.management import ManagementUtility


class RsyslogConfig:
    CONFIG_FILE = "/etc/rsyslog.conf"
    SENTINEL = "# Added by hydra-server\n"

    def __init__(self, config_file = None):
        self.config_file = config_file or self.CONFIG_FILE

    def remove(self):
        """Remove our config section from the rsyslog config file, or do
        nothing if our section is not there"""
        rsyslog_lines = open(self.config_file).readlines()
        try:
            config_start = rsyslog_lines.index(self.SENTINEL)
            rsyslog_lines.remove(self.SENTINEL)
            config_end = rsyslog_lines.index(self.SENTINEL)
            rsyslog_lines.remove(self.SENTINEL)
            rsyslog_lines = rsyslog_lines[:config_start] + rsyslog_lines[config_end:]
            open(self.config_file, 'w').write("".join(rsyslog_lines))
        except ValueError:
            # Missing start or end sentinel, cannot remove, ignore
            pass

    def add(self, database, server, user, port = None, password = None):
        #:ommysql:database-server,database-name,database-userid,database-password
        config_lines = []
        config_lines.append(self.SENTINEL)
        config_lines.extend([
                    "$ModLoad imtcp.so\n",
                    "$InputTCPServerRun 514\n",
                    "$ModLoad ommysql\n"])
        if port:
            config_lines.append("$ActionOmmysqlServerPort %d\n" % port)

        action_line = "*.*       :ommysql:%s,%s,%s" % (server, database, user)
        if password:
            action_line += ",%s" % password
        action_line += "\n"
        config_lines.append(action_line)
        config_lines.append(self.SENTINEL)

        rsyslog = open(self.config_file, 'a')
        rsyslog.writelines(config_lines)


class CommandError(Exception):
    pass


class ServiceConfig:
    def try_shell(self, cmdline, mystdout = subprocess.PIPE,
                  mystderr = subprocess.PIPE):
        rc, out, err = self.shell(cmdline, mystdout, mystderr)

        if rc != 0:
            log.error("Command failed: %s" % cmdline)
            log.error("returned: %s" % rc)
            log.error("stdout:\n%s" % out)
            log.error("stderr:\n%s" % err)
            raise CommandError("Command failed %s" % cmdline)
        else:
            return rc, out, err

    def shell(self, cmdline, mystdout = subprocess.PIPE,
              mystderr = subprocess.PIPE):
        p = subprocess.Popen(cmdline, stdout = mystdout, stderr = mystderr)
        out, err = p.communicate()
        rc = p.wait()
        return rc, out, err

    def _db_accessible(self):
        """Discover whether we have a working connection to the database"""
        from MySQLdb import OperationalError
        try:
            from django.db import connection
            connection.introspection.table_names()
            return True
        except OperationalError:
            return False

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
            return False

    def _db_current(self):
        """Discover whether there are any outstanding migrations to be
           applied"""
        if not self._db_populated():
            return False

        from south.models import MigrationHistory
        applied_migrations = MigrationHistory.objects.all().values('app_name', 'migration')
        applied_migrations = [(mh['app_name'], mh['migration']) for mh in applied_migrations]

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
        return self._db_current() and self._users_exist()

    def _setup_rsyslog(self, database):
        log.info("Writing rsyslog configuration")
        rsyslog = RsyslogConfig()
        rsyslog.remove()
        rsyslog.add(database['NAME'],
                    database['HOST'] or 'localhost',
                    database['USER'],
                    database['PORT'] or None,
                    database['PASSWORD'] or None)

    def _start_rsyslog(self):
        log.info("Restarting rsyslog")
        self.try_shell(["chkconfig", "rsyslog", "on"])
        self.try_shell(['service', 'rsyslog', 'restart'])

    def _setup_rabbitmq(self):
        RABBITMQ_USER = "hydra"
        RABBITMQ_PASSWORD = "hydra123"
        RABBITMQ_VHOST = "hydravhost"

        log.info("Starting RabbitMQ...")
        self.try_shell(["chkconfig", "rabbitmq-server", "on"])
        # FIXME: there's really no sane reason to have to set the stderr and
        #        stdout to None here except that subprocess.PIPE ends up
        #        blocking subprocess.communicate().
        #        we need to figure out why
        self.try_shell(["service", "rabbitmq-server", "restart"],
                       mystderr = None, mystdout = None)

        rc, out, err = self.try_shell(["rabbitmqctl", "-q", "list_users"])
        users = [line.split()[0] for line in out.split("\n") if len(line)]
        if not RABBITMQ_USER in users:
            log.info("Creating RabbitMQ user...")
            self.try_shell(["rabbitmqctl", "add_user", RABBITMQ_USER, RABBITMQ_PASSWORD])

        rc, out, err = self.try_shell(["rabbitmqctl", "-q", "list_vhosts"])
        vhosts = [line.split()[0] for line in out.split("\n") if len(line)]
        if not RABBITMQ_VHOST in vhosts:
            log.info("Creating RabbitMQ vhost...")
            self.try_shell(["rabbitmqctl", "add_vhost", RABBITMQ_VHOST])

        self.try_shell(["rabbitmqctl", "set_permissions", "-p", RABBITMQ_VHOST, RABBITMQ_USER, ".*", ".*", ".*"])

    def _enable_services(self):
        log.info("Enabling Chroma daemons")
        self.try_shell(['chkconfig', '--add', 'hydra-worker'])
        self.try_shell(['chkconfig', '--add', 'hydra-storage'])
        self.try_shell(['chkconfig', '--add', 'hydra-host-discover'])

    def _start_services(self):
        log.info("Starting Chroma daemons")
        self.try_shell(['service', 'hydra-worker', 'start'])
        self.try_shell(['service', 'hydra-storage', 'start'])
        self.try_shell(['service', 'hydra-host-discover', 'start'])

    def _stop_services(self):
        log.info("Stopping Chroma daemons")
        self.try_shell(['service', 'hydra-worker', 'stop'])
        self.try_shell(['service', 'hydra-storage', 'stop'])
        self.try_shell(['service', 'hydra-host-discover', 'stop'])

    def _setup_mysql(self, database):
        log.info("Setting up MySQL daemon...")
        self.try_shell(["service", "mysqld", "restart"])
        self.try_shell(["chkconfig", "mysqld", "on"])

        log.info("Creating database '%s'...\n" % database['NAME'])
        self.try_shell(["mysql", "-e", "create database %s;" % database['NAME']])

    def _user_account_prompt(self):
        log.info("Chroma will now create an initial administrative user using the" +
                 "credentials which you provide.")

        valid = False
        while not valid:
            username = raw_input("Username:")
            email = raw_input("Email:")
            password1 = getpass.getpass("Password:")
            password2 = getpass.getpass("Confirm password:")

            # TODO: validate all fields (HYD-750)
            if password1 != password2:
                log.error("Passwords do not match!")
            else:
                valid = True
        return username, email, password1

    def _setup_database(self, username = None, password = None):
        if not self._db_accessible():
            # For the moment use the builtin configuration
            # TODO: this is where we would establish DB name and credentials
            databases = settings.DATABASES
            self._setup_mysql(databases['default'])
            self._setup_rsyslog(databases['default'])
        else:
            log.info("MySQL already accessible")

        self._start_rsyslog()

        if not self._db_current():
            log.info("Creating database tables...")
            ManagementUtility(['', 'syncdb', '--noinput', '--migrate']).execute()
        else:
            log.info("Database tables already OK")

        if not self._users_exist():
            if not username:
                username, email, password = self._user_account_prompt()
            else:
                email = ""
            user = User.objects.create_superuser(username, email, password)
            user.groups.add(Group.objects.get(name='superusers'))
            log.info("User '%s' successfully created." % username)
        else:
            log.info("User accounts already created")

        # FIXME: we do this here because running management commands requires a working database,
        # but that shouldn't be so (ideally the /static/ dir would be built into the RPM)
        # (Django ticket #17656)
        log.info("Building static directory...")
        ManagementUtility(['', 'collectstatic', '--noinput']).execute()

    def setup(self, username = None, password = None):
        self._setup_database(username, password)
        self._setup_rabbitmq()
        self._enable_services()

        self._start_services()

        return self.validate()

    def start(self):
        if not self._db_current():
            log.error("Cannot start, database not configured")
            return
        self._start_services()

    def stop(self):
        if not self._db_current():
            log.error("Cannot start, database not configured")
            return
        self._stop_services()

    def _service_config(self, interesting_services = None):
        """Interrogate the current status of services"""
        log.info("Checking service configuration...")

        rc, out, err = self.try_shell(['chkconfig', '--list'])
        services = {}
        for line in out.split("\n"):
            if not line:
                continue

            tokens = line.split()
            service_name = tokens[0]
            if interesting_services and service_name not in interesting_services:
                continue

            enabled = (tokens[4][2:] == 'on')

            rc, out, err = self.shell(['service', service_name, 'status'])
            running = (rc == 0)

            services[service_name] = {'enabled': enabled, 'running': running}
        return services

    def validate(self):
        errors = []
        if not self._db_accessible():
            errors.append("Cannot connect to database")
        elif not self._db_current():
            errors.append("Database tables out of date")
        elif not self._users_exist():
            errors.append("No user accounts exist")

        interesting_services = ['hydra-worker', 'hydra-storage', 'hydra-host-discover', 'mysqld', 'rsyslog', 'rabbitmq-server']
        service_config = self._service_config(interesting_services)
        for s in interesting_services:
            try:
                service_status = service_config[s]
                if not service_status['enabled']:
                    errors.append("Service %s not set to start at boot" % s)
                if not service_status['running']:
                    errors.append("Service %s is not running" % s)
            except KeyError:
                errors.append("Service %s not found" % s)

        return errors

    def _write_local_settings(self, databases):
        # Build a local_settings file
        import os
        project_dir = os.path.dirname(os.path.realpath(settings.__file__))
        local_settings = os.path.join(project_dir, settings.LOCAL_SETTINGS_FILE)
        local_settings_str = ""
        local_settings_str += "CELERY_RESULT_BACKEND = \"database\"\n"
        local_settings_str += "CELERY_RESULT_DBURI = \"mysql://%s:%s@%s%s/%s\"\n" % (
                databases['default']['USER'],
                databases['default']['PASSWORD'],
                databases['default']['HOST'] or "localhost",
                ":%d" % databases['default']['PORT'] if databases['default']['PORT'] else "",
                databases['default']['NAME'])

        # Usefully, a JSON dict looks a lot like python
        import json
        local_settings_str += "DATABASES = %s\n" % json.dumps(databases, indent=4).replace("null", "None")

        # Dump local_settings_str to local_settings
        open(local_settings, 'w').write(local_settings_str)

        # TODO: support SERVER_HTTP_URL
        # TODO: support LOG_SERVER_HOSTNAME
