#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import subprocess
from chroma_agent.agent_daemon import daemon_log


def run(arg_list, shell = False):
    """Run a subprocess, and return a tuple of rc, stdout, stderr.

    Note: we buffer all output, so do not run commands with large outputs
    using this function.
    """

    daemon_log.info("shell.run: %s" % arg_list)
    import sys
    import pty
    import fcntl
    import os
    import select

    # some tools ~cough~crm~cough~ like to prettify they output, even
    # when they are not supposed to ~cough~-D~cough~ so let's not give
    # them enough information to even try to prettify
    os.environ["TERM"] = ""

    # Create a PTY in order to get libc in child processes
    # to use line-buffered instead of buffered mode on stdout
    master, slave = pty.openpty()
    stdout_file = os.fdopen(master)

    p = subprocess.Popen(arg_list, shell = shell,
                         stdout = slave,
                         stderr = subprocess.PIPE,
                         close_fds = True)

    # Set O_NONBLOCK on stdout and stderr, in order to use select.poll later
    flags = fcntl.fcntl(master, fcntl.F_GETFL)
    fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    flags = fcntl.fcntl(p.stderr, fcntl.F_GETFL)
    fcntl.fcntl(p.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # Create a poll object and register
    all_poll_flags = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR | select.POLLNVAL
    poll = select.poll()
    poll.register(p.stderr, all_poll_flags)
    poll.register(master, all_poll_flags)

    def teardown(p, poll, slave):
        poll.unregister(p.stderr)
        poll.unregister(master)
        del poll

        if p.stdin:
            p.stdin.close()
        if p.stdout:
            p.stdout.close()
        if p.stderr:
            p.stderr.close()
        stdout_file.close()
        #os.close(master) # bad file descriptor
        os.close(slave)
        del p

    try:
        # We will iterate on poll.poll until we have seen HUPs on both
        # stdout and stderr.
        stdout_buf = ""
        stderr_buf = ""

        # Support older pythons which don't define select.PIPE_BUF
        try:
            pipe_buf = select.PIPE_BUF
        except AttributeError:
            pipe_buf = 4096

        stdout_closed = False
        stderr_closed = False
        while (not stdout_closed) and (not stderr_closed):
            result = poll.poll(100)
            for fd, mask in result:
                if fd == master and mask & (select.POLLIN | select.POLLPRI):
                    import os
                    stdout = stdout_file.read(pipe_buf)
                    # FIXME: wtf?  I'm getting DOS newlines sometimes
                    stdout = stdout.replace("\r\n", "\n")
                    stdout_buf = stdout_buf + stdout
                    sys.stderr.write(stdout)
                elif fd == p.stderr.fileno() and mask & (select.POLLIN | select.POLLPRI):
                    stderr = p.stderr.read(pipe_buf)
                    stderr_buf = stderr_buf + stderr
                    sys.stderr.write(stderr)
                elif mask & select.POLLHUP:
                    if fd == master:
                        stdout_closed = True
                    elif fd == p.stderr.fileno():
                        stderr_closed = True
                    else:
                        raise RuntimeError("Unexpected select() result %s" % ((fd, mask),))
                else:
                    raise RuntimeError("Unexpected select() result %s" % ((fd, mask),))
        rc = p.wait()

        teardown(p, poll, slave)
    except Exception:
        teardown(p, poll, slave)
        raise

    return rc, stdout_buf, stderr_buf


def try_run(arg_list, shell = False):
    """Run a subprocess, and raise an exception if it returns nonzero.  Return
    stdout string."""
    rc, stdout, stderr = run(arg_list, shell)
    if rc != 0:
        raise RuntimeError("Error (%s) running '%s': '%s' '%s'" % (rc, " ".join(arg_list), stdout, stderr))

    return stdout
