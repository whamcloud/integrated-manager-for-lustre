# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import sys
import traceback

'''
This allows code to be placed in safe space for production (?) where uncaught exceptions are captured and logged
but passed not further. This means we can have a resilient application for production but see all the badness in
test / development. Use carefully to sandbox functionality.

It is implemented as a context handler and a decorator so that the user can use the most appropriate implementation
for there needs.
'''


def exceptionSandBox(logger, exception_value, message='Exception raised in sandbox'):
    def real_decorator(function):
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception:
                ex_type, ex, tb = sys.exc_info()
                data = traceback.format_exc(tb).splitlines()
                logger.debug('%s:\n%s' % (message + ' START',
                                          '\n'.join(data[1:] + [message + ' END'])))
            return exception_value
        return wrapper

    return real_decorator
