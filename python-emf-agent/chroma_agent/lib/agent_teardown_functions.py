# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


agent_daemon_teardown_functions = []


def agent_daemon_teardown_function():
    """
    A decorator for connecting method to teardown. A method decorated with this will be called each time the
    daemon is terminated normally.
    """

    def _decorator(func):
        agent_daemon_teardown_functions.append(func)
        return func

    return _decorator
