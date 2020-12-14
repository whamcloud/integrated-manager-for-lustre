# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
