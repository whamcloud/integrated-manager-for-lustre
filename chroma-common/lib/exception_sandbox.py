#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2017 Intel Corporation All Rights Reserved.
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
                                          '\n'.join(data[1:3] + ['  ...'] + data[-3:] + [message + ' END'])))
            return exception_value
        return wrapper

    return real_decorator
