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


agent_daemon_startup_functions = []


def agent_daemon_startup_function():
    """
    A decorator for connecting method to startup. A method decorated with this will be called each time the
    daemon is run. The call will occur just before the agent starts receiving commands from the manager.

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

    """
    def _decorator(func):
        agent_daemon_startup_functions.append(func)
        return func

    return _decorator
