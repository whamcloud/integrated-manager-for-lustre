# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import subprocess
import os
import sys
import logging
import time
import settings
import re
import uuid
import requests_unixsocket
import requests
from threading import Thread
from threading import Event


def all_subclasses(obj):
    """Used to introspect all descendents of a class.  Used because metaclasses
    are a PITA when doing multiple inheritance"""
    sc_recr = []
    for sc_obj in obj.__subclasses__():
        sc_recr.append(sc_obj)
        sc_recr.extend(all_subclasses(sc_obj))
    return sc_recr


def time_str(dt):
    return time.strftime("%Y-%m-%dT%H:%M:%S", dt.timetuple())


def sizeof_fmt(num):
    # http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size/1094933#1094933
    for x in ["bytes", "KB", "MB", "GB", "TB", "EB", "ZB", "YB"]:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0


def target_label_split(label):
    """
    Split a target label into a tuple of it's parts: (fsname, target type, index)
    """
    a = label.rsplit("-", 1)
    if len(a) == 1:
        # MGS
        return (None, a[0][0:3], None)
    return (a[0], a[1][0:3], int(a[1][3:], 16))


class dbperf(object):
    enabled = False
    logger = logging.getLogger("dbperf")

    def __init__(self, label=""):
        # Avoid importing this at module scope in order
        # to co-habit with chroma_settings()
        from django.db import connection

        self.connection = connection

        self.label = label
        self.logger.disabled = not self.enabled
        if self.enabled and not len(self.logger.handlers):
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(logging.FileHandler("dbperf.log"))

    def __enter__(self):
        if settings.DEBUG:
            self.t_initial = time.time()
            self.q_initial = len(self.connection.queries)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.enabled:
            return

        self.t_final = time.time()
        self.q_final = len(self.connection.queries)

        t = self.t_final - self.t_initial
        q = self.q_final - self.q_initial

        if q:
            logfile = open("%s.log" % self.label, "w")
            for query in self.connection.queries[self.q_initial :]:
                logfile.write("(%s) %s\n" % (query["time"], query["sql"]))
            logfile.close()

        if q:
            avg_t = int((t / q) * 1000)
        else:
            avg_t = 0
        self.logger.debug("%s: %d queries in %.2fs (avg %dms)" % (self.label, q, t, avg_t))
        self.q = q


def site_dir():
    def _search_path(path):
        if os.path.exists(os.path.join(path, "settings.py")):
            return path
        else:
            if path == "/":
                raise RuntimeError("Can't find settings.py")
            else:
                return _search_path(os.path.dirname(path))

    return _search_path(os.path.dirname(__file__))


def chroma_settings():
    """
    Walk back up parent directories until settings.py is found.
    Insert that directory as the first entry in sys.path.
    Import the settings module, then return it to the caller.
    """

    sys.path.insert(0, site_dir())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    import settings

    return settings


class CommandError(Exception):
    def __init__(self, cmd, rc, stdout, stderr):
        self.cmd = cmd
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return """Command failed: %s
    return code %s
    stdout: %s
    stderr: %s""" % (
            self.cmd,
            self.rc,
            self.stdout,
            self.stderr,
        )


class CommandLine(object):
    def try_shell(self, cmdline, mystdout=subprocess.PIPE, mystderr=subprocess.PIPE, stdin_text=None, shell=False):
        rc, out, err = self.shell(cmdline, mystdout, mystderr, stdin_text, shell=shell)

        if rc != 0:
            raise CommandError(cmdline, rc, out, err)
        else:
            return rc, out, err

    def shell(self, cmdline, mystdout=subprocess.PIPE, mystderr=subprocess.PIPE, stdin_text=None, shell=False):
        if stdin_text is not None:
            stdin = subprocess.PIPE
        else:
            stdin = None
        p = subprocess.Popen(cmdline, stdout=mystdout, stderr=mystderr, stdin=stdin, shell=shell)
        if stdin_text is not None:
            p.stdin.write(stdin_text)
        out, err = p.communicate()
        rc = p.wait()
        return rc, out, err


def runningInDocker():
    with open("/proc/self/cgroup", "r") as procfile:
        for line in procfile:
            fields = line.strip().split("/")
            if fields[1] == "docker":
                return True
    return False


def post_data_to_tcp_or_socket(post_data):
    if runningInDocker():
        return requests.post("http://{}:{}".format(settings.PROXY_HOST, settings.ACTION_RUNNER_PORT), json=post_data)

    SOCKET_PATH = "http+unix://%2Fvar%2Frun%2Fiml-action-runner.sock/"
    return requests_unixsocket.post(SOCKET_PATH, json=post_data)


def start_action_local_with_tcp_or_socket(command, args, request_id):
    post_data = {"LOCAL": {"type": "ACTION_START", "action": command, "args": args, "id": str(request_id)}}
    return post_data_to_tcp_or_socket(post_data)


def cancel_action_local_with_tcp_or_socket(request_id):
    post_data = {"LOCAL": {"type": "ACTION_CANCEL", "id": str(request_id)}}
    return post_data_to_tcp_or_socket(post_data)


def start_action_with_tcp_or_socket(host, command, args, request_id):
    post_data = {"REMOTE": (host, {"type": "ACTION_START", "action": command, "args": args, "id": str(request_id)})}
    return post_data_to_tcp_or_socket(post_data)


def cancel_action_with_tcp_or_socket(host, request_id):
    post_data = {"REMOTE": (host, {"type": "ACTION_CANCEL", "id": str(request_id)})}
    return post_data_to_tcp_or_socket(post_data)


class RustAgentCancellation(Exception):
    pass


def invoke_rust_local_action(command, args={}, cancel_event=Event()):
    """
    Talks to the iml-action-runner service
    """

    request_id = uuid.uuid4()

    trigger = Event()

    class ActionResult:
        ok = None
        error = None

    def start_action(ActionResult, trigger):
        try:
            ActionResult.ok = start_action_local_with_tcp_or_socket(command, args, request_id).content
        except Exception as e:
            ActionResult.error = e
        finally:
            trigger.set()

    t = Thread(target=start_action, args=(ActionResult, trigger))

    t.start()

    # Wait for action completion, waking up every second to
    # check cancel_event
    while True:
        if cancel_event.is_set():
            cancel_action_local_with_tcp_or_socket(request_id).content
            raise RustAgentCancellation()
        else:
            trigger.wait(timeout=1.0)
            if trigger.is_set():
                break

    if ActionResult.error is not None:
        raise ActionResult.error
    else:
        return ActionResult.ok


def invoke_rust_agent(host, command, args={}, cancel_event=Event()):
    """
    Talks to the iml-action-runner service
    """

    request_id = uuid.uuid4()

    trigger = Event()

    class ActionResult:
        ok = None
        error = None

    def start_action(ActionResult, trigger):
        try:
            ActionResult.ok = start_action_with_tcp_or_socket(host, command, args, request_id).content
        except Exception as e:
            ActionResult.error = e
        finally:
            trigger.set()

    t = Thread(target=start_action, args=(ActionResult, trigger))

    t.start()

    # Wait for action completion, waking up every second to
    # check cancel_event
    while True:
        if cancel_event.is_set():
            cancel_action_with_tcp_or_socket(host, request_id).content
            raise RustAgentCancellation()
        else:
            trigger.wait(timeout=1.0)
            if trigger.is_set():
                break

    if ActionResult.error is not None:
        raise ActionResult.error
    else:
        return ActionResult.ok
