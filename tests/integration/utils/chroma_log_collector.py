#
# Simple script to gather all of the relevant logs from a cluster.
#
# Usage: ./chroma_log_collection.py destination_path cluster_cfg_path
#   destination_path - the directory to copy all of the log files into
#   cluster_cfg_path - the path to the cluster config file
#
# Ex usage: ./chroma_log_collection.py ss_log_collection_test some_machine:~/cluster_cfg.json

import json
import re
import sys
import tempfile
import subprocess
import time
import collections

RunResult = collections.namedtuple("RunResult", ["rc", "stdout", "stderr", "timeout"])


def shell_run(arg_list, timeout=0xFFFFFFF):
    """Basic routine to run a shell command.

    Effectively no autotimeout for commands.

    """

    assert type(arg_list) in [list, str, unicode], "arg list must be list or str :%s" % type(arg_list)

    # Allow simple commands to just be presented as a string. However do not start formatting the string this
    # will be rejected in a code review. If it has args present them as a list.
    if type(arg_list) in [str, unicode]:
        arg_list = arg_list.split()

    # Popen has a limit of 2^16 for the output if you use subprocess.PIPE (as we did recently) so use real files so
    # the output side is effectively limitless
    stdout_fd = tempfile.TemporaryFile()
    stderr_fd = tempfile.TemporaryFile()

    try:
        p = subprocess.Popen(arg_list, stdout=stdout_fd, stderr=stderr_fd, close_fds=True)

        # Rather than using p.wait(), we do a slightly more involved poll/backoff, in order
        # to poll the thread_state.teardown event as well as the completion of the subprocess.
        # This is done to allow cancellation of subprocesses
        rc = None
        max_wait = 1.0
        wait = 1.0e-3
        timeout += time.time()
        while rc is None:
            rc = p.poll()
            if rc is None:
                time.sleep(1)

                if time.time() > timeout:
                    p.kill()
                    stdout_fd.seek(0)
                    stderr_fd.seek(0)
                    return RunResult(
                        254,
                        stdout_fd.read().decode("ascii", "ignore"),
                        stderr_fd.read().decode("ascii", "ignore"),
                        True,
                    )
                elif wait < max_wait:
                    wait *= 2.0
            else:
                stdout_fd.seek(0)
                stderr_fd.seek(0)
                return RunResult(
                    rc, stdout_fd.read().decode("ascii", "ignore"), stderr_fd.read().decode("ascii", "ignore"), False
                )
    finally:
        stdout_fd.close()
        stderr_fd.close()


class ChromaLogCollector(object):
    def __init__(self, destination_path, chroma_managers, lustre_servers, test_runners, *args, **kwargs):
        super(ChromaLogCollector, self).__init__(*args, **kwargs)
        self.destination_path = destination_path
        self.chroma_managers = chroma_managers
        self.lustre_servers = lustre_servers
        self.test_runners = test_runners

    def collect_logs(self):
        """Collect the logs from the target.

        :return: empty list on success or error messages that can be used
            for diagnosing what went wrong.

        """
        if shell_run(["rm", "-rf", "%s/*.log" % destination_path]).rc:
            return "Fail to clear out destination path for logs collection: %s" % destination_path

        errors = []

        for test_runner in self.test_runners:
            errors.append(self.fetch_log(test_runner, "/var/log/chroma_test.log", "%s-chroma_test.log" % test_runner))
            errors.append(self.fetch_log(test_runner, "/var/log/messages", "%s-messages.log" % test_runner))

        for server in self.chroma_managers + self.lustre_servers:
            errors.append(self.fetch_log(server, "/var/log/yum.log", "%s-yum.log" % server))
            errors.extend(self.fetch_iml_diagnostics(server))

        return [error for error in errors if error]

    def fetch_log(self, server, source_log_path, destination_log_filename):
        """Collect the log from the target.

        :return: None on success or error message that can be
        used for diagnosing what went wrong.

        """
        action = "Fetching %s from %s to %s/%s" % (
            source_log_path,
            server,
            self.destination_path,
            destination_log_filename,
        )
        print(action)
        if shell_run(
            ["scp", "%s:%s" % (server, source_log_path), "%s/%s" % (self.destination_path, destination_log_filename)]
        ).rc:
            error = "Failed %s" % action

            with open(destination_log_filename, "w+") as f:
                f.write(error)
            return error

        return None

    def fetch_log_dir(self, server, dir):
        """Collect the log directory from the target.

        :return: None on success or error message that can be used for diagnosing what went wrong.

        """
        logs = shell_run(["ssh", server, "ls %s | xargs -n1 basename" % dir])

        if logs.rc:
            return "Failed fecthing log dir %s from %s" % (server, dir)

        for log in logs.stdout.split():
            destination_log_filename = "%s-%s-%s" % (server, dir.strip("/").split("/")[-1], log)
            self.fetch_log(server, "%s/%s" % (dir, log), destination_log_filename)

        return None

    def fetch_iml_diagnostics(self, server):
        """Collect the iml diagnostics from the target.

        :return: empty list on success or list of error messages that can be
            used for diagnosing what went wrong.

        """

        # Install iml_sos_plugin if not already installed
        if shell_run(["ssh", server, "yum -y install iml_sos_plugin"]).rc:
            return ["iml_sos_plugin failed to install on %s. skipping." % server]

        # Generate the diagnostics from the server
        result = shell_run(["ssh", server, "iml-diagnostics", "--all-logs"], timeout=600)

        if result.timeout:
            return ["IML Diagnostics timed-out"]

        # Find the diagnostics filename from the iml-diagnostics output
        cd_out = result.stdout.decode("utf8")
        match = re.compile("/var/tmp/(sosreport-.*\.tar\..*)").search(cd_out)
        if not match:
            return [
                "Did not find diagnostics filepath in iml-diagnostics output:\nstderr:\n%s\nstdout:\n%s"
                % (cd_out, result.stdout.decode("utf8"))
            ]
        diagnostics = match.group(1).strip()

        errors = []

        # Copy and expand the diagnostics locally, so they will be
        # able to be read in browser in Jenkins.
        errors.append(self.fetch_log(server, "/var/tmp/%s" % diagnostics, ""))

        if diagnostics.endswith("tar.xz"):
            if shell_run(
                ["tar", "-xvJf", "%s/%s" % (self.destination_path, diagnostics), "-C", self.destination_path]
            ).rc:
                errors.append("Error tar --xvJf the iml diagnostics file")
        elif diagnostics.endswith("tar.gz"):
            if shell_run(
                ["tar", "-xvzf", "%s/%s" % (self.destination_path, diagnostics), "-C", self.destination_path]
            ).rc:
                errors.append("Error tar -xvzf the iml diagnostics file")
        else:
            errors = "Didn't recognize iml-diagnostics file format"

        diagnostics_dir = re.compile("(sosreport-.*)\.tar\..*").search(diagnostics).group(1)

        if shell_run(["chmod", "-R", "777", "%s/%s" % (self.destination_path, diagnostics_dir)]).rc:
            errors.append(
                "Unable to change perms on expanded diagnostics at %s/%s" % (self.destination_path, diagnostics_dir)
            )

        if shell_run(["rm", "-f", "%s/%s" % (self.destination_path, diagnostics)]).rc:
            errors.append("Unable to remove the diagnostics %s/%s" % (self.destination_path, diagnostics))

        return errors


if __name__ == "__main__":

    destination_path = sys.argv[1]
    cluster_cfg_path = sys.argv[2]

    shell_run(["mkdir", "-p", destination_path])
    shell_run(["rm", "-f", "%s.tgz" % destination_path])
    cluster_cfg_json = open(cluster_cfg_path)
    cluster_cfg = json.loads(cluster_cfg_json.read())

    chroma_managers = []
    for chroma_manager in cluster_cfg["chroma_managers"]:
        chroma_managers.append("root@%s" % chroma_manager["address"])

    lustre_servers = []
    for lustre_server in cluster_cfg["lustre_servers"]:
        if not lustre_server["distro"] == "mock":
            lustre_servers.append("root@%s" % lustre_server["address"])

    test_runners = []
    for test_runner in cluster_cfg["test_runners"]:
        test_runners.append("root@%s" % test_runner["address"])

    log_collector = ChromaLogCollector(destination_path, chroma_managers, lustre_servers, test_runners)
    errors = log_collector.collect_logs()

    if errors:
        print("\n".join(errors))
        sys.exit(1)
