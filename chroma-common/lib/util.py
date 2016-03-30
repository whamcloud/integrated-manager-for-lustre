#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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
import threading
import platform
from collections import namedtuple
from collections import MutableSequence
import sys

ExpiringValue = namedtuple('ExpiringValue', ['value', 'expiry'])


class ExpiringList(MutableSequence):
    """Special implementation of a python list which invalidate its elements after a specified
    'grace_period'
    """

    def __init__(self, grace_period):
        self._container = list()
        self.grace_period = grace_period

    def __len__(self):
        return len([x for x in self])

    def __delitem__(self, index):
        del self._container[index]

    def __setitem__(self, index, value):
        self.insert(index, value)

    def __str__(self):
        return str([x for x in self])

    def __getitem__(self, index):
        cur_time = time.time()
        if cur_time > self._container[index].expiry:
            self._container = [x for x in self._container if x.expiry >= cur_time]
        return self._container[index].value

    def insert(self, index, value):
        self._container.insert(index, ExpiringValue(value, time.time() + self.grace_period))


class ExceptionThrowingThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        # Sometimes not threading helps with debug.
        self._use_threads = kwargs.pop('use_threads', True)

        if self._use_threads:
            super(ExceptionThrowingThread, self).__init__(*args, **kwargs)
        self._call_target = kwargs['target']
        self._call_args = kwargs['args']
        self._exception_value = None

    def run(self):
        try:
            return super(ExceptionThrowingThread, self).run()
        except BaseException as e:
            self._exception_value = e

    def start(self):
        if self._use_threads:
            return super(ExceptionThrowingThread, self).start()
        else:
            try:
                self._call_target(*self._call_args)
            except BaseException as e:
                self._exception_value = e

    def join(self):
        if self._use_threads:
            super(ExceptionThrowingThread, self).join()
        if self._exception_value:
            raise self._exception_value

    @classmethod
    def wait_for_threads(cls, threads):
        """Wait for all the threads to finish raising an exception if any of them raise an exception
        We have to capture and then raise one of them because we can't re-raise all of the
        exceptions. We do this to make sure all the threads exit before we start the next test.
        """

        exception_raised = None

        for thread in threads:
            try:
                thread.join()
            except Exception as e:
                exception_raised = e

        if exception_raised:
            raise exception_raised


def all_subclasses(klass):
    """
    :return: All the subclasses of the class passed, scanning the inheritance tree recursively
             to find ALL the subclasses.
    """
    return klass.__subclasses__() + [child for subclass in klass.__subclasses__() for child in
                                     all_subclasses(subclass)]


def enum(*sequential, **named):
    """Return enumerated type object from list of keyword and positional arguments
    Reverse access to Enum identifiers available through 'reverse_mapping' member
    :param sequential: positional arguments
    :param named: keyword arguments
    :return: Enum type object with numbered (sequential) or explicit value (keyword) attributes
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)


PlatformInfo = namedtuple('PlatformInfo', ['system',
                                           'distro',
                                           'distro_version',
                                           'distro_version_full',  # note this returns a string e.g. '6.7.1455'
                                           'python_version_major_minor',
                                           'python_patchlevel',
                                           'kernel_version'])

"""A more readable version of the standard platform commands. Using a named tuple the
usage should be much easier to fathom. Caches the value for speed which presumes
the contents are constant for a given execution.

For a Mac it pretends to be Centos 6.7.

:return: PlatformInfo named tuple
"""
if 'nosetests' in sys.argv[0]:
    # default platform_info attributes for agent unit tests (el6)
    platform_info = PlatformInfo('Linux',
                                 'CentOS',
                                 6.7,
                                 '6.7.1552',
                                 2.6,
                                 6,
                                 '2.6.32-504.12.2.el6.x86_64')
elif platform.system() == 'Linux':
    platform_info = PlatformInfo(platform.system(),
                                 platform.linux_distribution()[0],
                                 float('.'.join(platform.linux_distribution()[1].split('.')[:2])),
                                 platform.linux_distribution()[1],
                                 float("%s.%s" % (platform.python_version_tuple()[0],
                                                  platform.python_version_tuple()[1])),
                                 int(platform.python_version_tuple()[2]),
                                 platform.release())
elif platform.system() == 'Darwin':
    platform_info = PlatformInfo('Linux',
                                 'CentOS',
                                 6.7,
                                 '6.7',
                                 float("%s.%s" % (platform.python_version_tuple()[0],
                                                  platform.python_version_tuple()[1])),
                                 int(platform.python_version_tuple()[2]),
                                 '2.6.32-504.12.2.el6.x86_64')
else:
    raise RuntimeError('Unknown system type %s' % platform.system())
