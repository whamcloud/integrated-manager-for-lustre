# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


agent_daemon_teardown_functions = []


def agent_daemon_teardown_function():
    """
    A decorator for connecting method to teardown. A method decorated with this will be called each time the
    daemon is terminated normally. The call will occur just before the agent stops receiving commands from the manager.

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

    """
    def _decorator(func):
        agent_daemon_teardown_functions.append(func)
        return func

    return _decorator
