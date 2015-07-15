import collections
import subprocess
import tempfile
import time

RunResult = collections.namedtuple("RunResult", ['timeout', 'rc', 'stdout', 'stderr'])


def run(arg_list, timeout=600):
    """
    Simple process that doesn't have problems associated with 64K Popen limit and times out.

    Popen has a limit of 2^16 for the output if you use subprocess.PIPE (as we did recently) so use real files so
    the output side is effectively limitless

    Fakes an rc=1000 for timeout
    """
    stdout_fd = tempfile.TemporaryFile()
    stderr_fd = tempfile.TemporaryFile()

    try:
        p = subprocess.Popen(arg_list,
                             stdout = stdout_fd,
                             stderr = stderr_fd,
                             close_fds = True)

        # Rather than using p.wait(), we do a slightly more involved poll/backoff,
        # this is done to allow cancellation of subprocesses
        rc = None
        wait = 1.0E-3
        max_wait = 1.0
        timeout += time.time()
        while rc is None:
            rc = p.poll()
            if rc is None:
                time.sleep(wait)
                if time.time() > timeout:
                    p.kill()
                    stdout_fd.seek(0)
                    stderr_fd.seek(0)
                    return RunResult(True, 254, stdout_fd.read(), stderr_fd.read())
                elif wait < max_wait:
                    wait *= 2.0
            else:
                stdout_fd.seek(0)
                stderr_fd.seek(0)
                return RunResult(False, rc, stdout_fd.read(), stderr_fd.read())
    finally:
        stdout_fd.close()
        stderr_fd.close()
