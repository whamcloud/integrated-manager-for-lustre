#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.
import time
import platform
import math
import abc
from chroma_agent.chroma_common.lib import util
from chroma_agent.lib.shell import AgentShell


class ServiceControl(object):

    class_override = None
    __metaclass__ = abc.ABCMeta

    def __init__(self, service_name):
        self.service_name = service_name

    @classmethod
    def create(cls, service_name):
        try:
            required_class = next(class_ for class_ in util.all_subclasses(cls) if class_._applicable())

            return required_class(service_name)
        except StopIteration:
            raise RuntimeError('Current platform version not applicable')

    def _retried_action(self, action, validate, error_message, retry_count, retry_time, validate_time):
        error = None
        retries = retry_count + 1
        while retries > 0:
            error = action()
            if error is None:
                time.sleep(validate_time)
                if validate():
                    return None
                error = error_message % self.service_name
            retries -= 1
            time.sleep(retry_time)
        return error

    def start(self, retry_count=5, retry_time=1, validate_time=5):
        return self._retried_action(lambda: self._start(),
                                    lambda: self.running,
                                    'Service %s is not running after being started',
                                    retry_count,
                                    retry_time,
                                    validate_time)

    def stop(self, retry_count=5, retry_time=1, validate_time=5):
        return self._retried_action(lambda: self._stop(),
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

    @abc.abstractproperty
    def running(self):
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


class ServiceControlRH6(ServiceControl):

    platform_use = 6

    @property
    def running(self):
        # Returns True if the service is running. "service servicename status"
        return AgentShell.run(['/sbin/service', self.service_name, 'status'])[0] == 0

    @property
    def enabled(self):
        # Returns True if the service is enabled. "chkconfig servicename"
        return AgentShell.run(['/sbin/chkconfig', self.service_name, 'status'])[0] == 0

    @classmethod
    def _applicable(cls):
        if platform.system() == 'Linux':
            platform_info = platform.linux_distribution()
            version = math.floor(float(platform_info[1]))
            if version == cls.platform_use:
                return True
            else:
                return False
        else:
            return False

    def add(self):
        return AgentShell.run_canned_error_message(['/sbin/chkconfig', '--add', self.service_name])

    def enable(self):
        return AgentShell.run_canned_error_message(['/sbin/chkconfig', self.service_name, 'on'])

    def reload(self):
        return AgentShell.run_canned_error_message(['/sbin/service', self.service_name, 'reload'])

    def disable(self):
        return AgentShell.run_canned_error_message(['/sbin/chkconfig', self.service_name, 'off'])

    def _start(self):
        return AgentShell.run_canned_error_message(['/sbin/service', self.service_name, 'start'])

    def _stop(self):
        return AgentShell.run_canned_error_message(['/sbin/service', self.service_name, 'stop'])


class ServiceControlRH7(ServiceControl):

    platform_use = 7

    @property
    def running(self):
        # Returns True if the service is running. "service servicename status"
        return AgentShell.run(['systemctl', 'is-active', self.service_name])[0] == 0

    @property
    def enabled(self):
        # Returns True if the service is enabled. "chkconfig servicename"
        return AgentShell.run(['systemctl', 'is-enabled', self.service_name])[0] == 0

    @classmethod
    def _applicable(cls):
        if platform.system() == 'Linux':
            platform_info = platform.linux_distribution()
            version = math.floor(float(platform_info[1]))
            if version == cls.platform_use:
                return True
            else:
                return False
        else:
            return False

    def add(self):
        pass

    def enable(self):
        return AgentShell.run_canned_error_message(['systemctl', 'enable', self.service_name])

    def reload(self):
        return AgentShell.run_canned_error_message(['systemctl', 'reload', self.service_name])

    def disable(self):
        return AgentShell.run_canned_error_message(['systemctl', 'disable', self.service_name])

    def _start(self):
        return AgentShell.run_canned_error_message(['systemctl', 'start', self.service_name])

    def _stop(self):
        return AgentShell.run_canned_error_message(['systemctl', 'stop', self.service_name])


class ServiceControlOSX(ServiceControlRH6):
    """ Just a stub class so that running on OSX things can be made to work.

    We make OSX behave like RH6 because that historically is what happened. So
    this class provides for backwards compatibility.
    """
    @classmethod
    def _applicable(cls):
        return platform.system() == 'Darwin'
