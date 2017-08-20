# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import time
import platform
import abc
from collections import defaultdict
from collections import namedtuple

from . import util
from . import shell


class ServiceControl(object):
    class_override = None
    __metaclass__ = abc.ABCMeta

    # dict to map service names to registered listener callbacks functions
    callbacks = defaultdict(list)

    ActionCode = namedtuple('ActionCode', ['before', 'after', 'error'])

    ServiceState = util.enum('SERVICESTARTING', 'SERVICESTARTED', 'SERVICESTARTERROR',
                             'SERVICESTOPPING', 'SERVICESTOPPED', 'SERVICESTOPERROR')

    def __init__(self, service_name):
        self.service_name = service_name

    @classmethod
    def create(cls, service_name):
        try:
            required_class = next(
                class_ for class_ in util.all_subclasses(cls) if class_._applicable())

            return required_class(service_name)
        except StopIteration:
            raise RuntimeError('Current platform not supported by any ServiceControl class')

    def _retried_action(self,
                        action,
                        action_codes,
                        validate,
                        error_message,
                        retry_count,
                        retry_time,
                        validate_time):
        """Try action fixed number of times and notify registered listeners with action
        before, after and error codes
        """
        error = None
        self.notify(self.service_name, action_codes.before)

        while retry_count > -1:
            error = action()

            if error is None:
                time.sleep(validate_time)

                # action completed successfully, validate the change
                if validate():
                    self.notify(self.service_name, action_codes.after)
                    return None

                # validation failed so populate error message
                error = error_message % self.service_name
            retry_count -= 1
            time.sleep(retry_time)

        # notify error if retries exceeded without success
        self.notify(self.service_name, action_codes.error)

        return error

    def start(self, retry_count=5, retry_time=1, validate_time=5):
        return self._retried_action(lambda: self._start(),
                                    self.ActionCode(self.ServiceState.SERVICESTARTING,
                                                    self.ServiceState.SERVICESTARTED,
                                                    self.ServiceState.SERVICESTARTERROR),
                                    lambda: self.running,
                                    'Service %s is not running after being started',
                                    retry_count,
                                    retry_time,
                                    validate_time)

    def stop(self, retry_count=5, retry_time=1, validate_time=5):
        return self._retried_action(lambda: self._stop(),
                                    self.ActionCode(self.ServiceState.SERVICESTOPPING,
                                                    self.ServiceState.SERVICESTOPPED,
                                                    self.ServiceState.SERVICESTOPERROR),
                                    lambda: not self.running,
                                    'Service %s is still running after being stopped',
                                    retry_count,
                                    retry_time,
                                    validate_time)

    def restart(self, retry_count=5, retry_time=1, validate_time=1):
        error = self.stop(retry_count, retry_time, validate_time)
        if error is None:
            error = self.start(retry_count, retry_time, validate_time)

        return error

    @classmethod
    def register_listener(cls, service, callback):
        """register a listening callback function to receive event notifications for a
        particular service's control events, applied through ServiceControl class instances
        """
        if not hasattr(callback, '__call__'):
            raise RuntimeError('callback parameter provided is not callable')
        # don't want duplicates in list of registered callbacks for a particular service
        if callback not in cls.callbacks[service]:
            cls.callbacks[service].append(callback)
        else:
            raise RuntimeError('callback already registered for service %s (%s)' % (service,
                                                                                    str(callback)))

    @classmethod
    def unregister_listener(cls, service, callback):
        """unregister a listening callback function to stop receive event notifications for a
        particular service's control events, applied through ServiceControl class instances
        """
        if not hasattr(callback, '__call__'):
            raise RuntimeError('callback parameter provided is not callable')
        # don't clear other callbacks registered for this service
        try:
            cls.callbacks[service].remove(callback)
        except ValueError:
            raise RuntimeError('callback function is not registered for service %s and cannot be '
                               'removed (%s)' % (service, str(callback)))

    @classmethod
    def notify(cls, service, action_code):
        """call registered callbacks for a particular service/action pair"""
        for callback in cls.callbacks[service]:
            callback(service, action_code)

    @abc.abstractproperty
    def running(self):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def daemon_reload(cls):
        """
        Only really applicable to systemctl, this cause the os system to reload the configuration of
        the controls, causes new or modified files to be re-read.
        """
        raise NotImplementedError

    @abc.abstractproperty
    def enabled(self):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _applicable(cls):
        raise NotImplementedError

    @abc.abstractmethod
    def enable(self):
        raise NotImplementedError

    @abc.abstractmethod
    def reload(self):
        raise NotImplementedError

    @abc.abstractmethod
    def disable(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _start(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _stop(self):
        raise NotImplementedError


class ServiceControlEL6(ServiceControl):

    platform_use = '6'

    @property
    def running(self):
        # Returns True if the service is running. "service servicename status"
        return shell.Shell.run(['/sbin/service', self.service_name, 'status']).rc == 0

    @property
    def enabled(self):
        # Returns True if the service is enabled. "chkconfig servicename"
        return shell.Shell.run(['/sbin/chkconfig', self.service_name]).rc == 0

    @classmethod
    def _applicable(cls):
        return util.platform_info.system == 'Linux' and \
               cls.platform_use == util.platform_info.distro_version_full.split('.')[0]

    @classmethod
    def daemon_reload(cls):
        pass

    def enable(self):
        return shell.Shell.run_canned_error_message(['/sbin/chkconfig', '--add', self.service_name]) or \
               shell.Shell.run_canned_error_message(['/sbin/chkconfig', self.service_name, 'on'])

    def reload(self):
        return shell.Shell.run_canned_error_message(['/sbin/service', self.service_name, 'reload'])

    def disable(self):
        return shell.Shell.run_canned_error_message(['/sbin/chkconfig', self.service_name, 'off'])

    def _start(self):
        return shell.Shell.run_canned_error_message(['/sbin/service', self.service_name, 'start'])

    def _stop(self):
        return shell.Shell.run_canned_error_message(['/sbin/service', self.service_name, 'stop'])


class ServiceControlEL7(ServiceControl):

    platform_use = '7'

    @property
    def running(self):
        # Returns True if the service is running.
        return shell.Shell.run(['systemctl', 'is-active', self.service_name]).rc == 0

    @property
    def enabled(self):
        # Returns True if the service is enabled.
        return shell.Shell.run(['systemctl', 'is-enabled', self.service_name]).rc == 0

    @classmethod
    def _applicable(cls):
        return util.platform_info.system == 'Linux' and \
               cls.platform_use == util.platform_info.distro_version_full.split('.')[0]

    @classmethod
    def daemon_reload(cls):
        shell.Shell.run(['systemctl', 'daemon-reload'])

    def enable(self):
        return shell.Shell.run_canned_error_message(['systemctl', 'enable', self.service_name])

    def reload(self):
        return shell.Shell.run_canned_error_message(['systemctl', 'reload', self.service_name])

    def disable(self):
        return shell.Shell.run_canned_error_message(['systemctl', 'disable', self.service_name])

    def _start(self):
        return shell.Shell.run_canned_error_message(['systemctl', 'start', self.service_name])

    def _stop(self):
        return shell.Shell.run_canned_error_message(['systemctl', 'stop', self.service_name])


class ServiceControlOSX(ServiceControlEL6):
    """ Just a stub class so that running on OSX things can be made to work.

    We make OSX behave like EL6 because that historically is what happened. So
    this class provides for backwards compatibility.
    """
    @classmethod
    def _applicable(cls):
        return platform.system() == 'Darwin'
