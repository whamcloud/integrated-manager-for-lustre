#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


import traceback

'''
This allows code to be placed in safe space for production (?) where uncaught exceptions are captured and logged
but passed not further. This means we can have a resilient application for production but see all the badness in
test / development. Use carefully to sandbox functionality.

It is implemented as a context handler and a decorator so that the user can use the most appropriate implementation
for there needs.
'''


class ExceptionSandBox(object):

    debug_on = None         # Set to none so we can trap someone not setting it.

    def __init__(self, logger):
        self.logger = logger

    def __enter__(self):
        pass

    def __exit__(self, exception_type, value, _traceback):
        assert ExceptionSandBox.debug_on != None

        if exception_type and not ExceptionSandBox.debug_on:
            backtrace = '\n'.join(traceback.format_exception(type, value, _traceback))
            self.logger.error("Unhandled error in thread %s: %s" % (self.__class__.__name__, backtrace))
            return True

    @classmethod
    def enable_debug(cls, debug_on):
        # debug_on means the exception is passed up and things get real bad!
        ExceptionSandBox.debug_on = debug_on


def exceptionSandBox(logger, exception_value):
    def real_decorator(function):
        def wrapper(*args, **kwargs):
            with ExceptionSandBox(logger):
                return function(*args, **kwargs)

            return exception_value
        return wrapper

    return real_decorator
