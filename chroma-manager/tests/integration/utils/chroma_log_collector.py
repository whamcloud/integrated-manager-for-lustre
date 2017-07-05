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

from chroma_common.lib.shell import Shell


class ChromaLogCollector(object):

    def __init__(self, destination_path, chroma_managers, lustre_servers, test_runners, *args, **kwargs):
        super(ChromaLogCollector, self).__init__(*args, **kwargs)
        self.destination_path = destination_path
        self.chroma_managers = chroma_managers
        self.lustre_servers = lustre_servers
        self.test_runners = test_runners

    def collect_logs(self):
        """
        Collect the logs from the target
        :return: empty list on success or error messages that can be used for diagnosing what went wrong.
        """
        if Shell.run(['rm', '-rf', "%s/*.log" % destination_path]).rc:
            return "Fail to clear out destination path for logs collection: %s" % destination_path

        errors = []

        for test_runner in self.test_runners:
            errors.append(self.fetch_log(test_runner, '/var/log/chroma_test.log', "%s-chroma_test.log" % test_runner))
            errors.append(self.fetch_log(test_runner, '/var/log/messages', "%s-messages.log" % test_runner))

        for server in self.chroma_managers + self.lustre_servers:
            errors.append(self.fetch_log(server, '/var/log/yum.log', "%s-yum.log" % server))
            errors.extend(self.fetch_chroma_diagnostics(server))

        return [error for error in errors if error]

    def fetch_log(self, server, source_log_path, destination_log_filename):
        """
        Collect the log from the target
        :return: None on success or error message that can be used for diagnosing what went wrong.
        """
        action = "Fetching %s from %s to %s/%s" % (source_log_path, server, self.destination_path, destination_log_filename)
        print action
        if Shell.run(['scp', "%s:%s" % (server, source_log_path), "%s/%s" % (
                self.destination_path, destination_log_filename)]).rc:
            error = "Failed %s" % action

            with open(destination_log_filename, "w+") as f:
                f.write(error)
            return error

        return None

    def fetch_log_dir(self, server, dir):
        """
        Collect the log directory from the target
        :return: None on success or error message that can be used for diagnosing what went wrong.
        """
        logs = Shell.run(['ssh', server, "ls %s | xargs -n1 basename" % dir])

        if logs.rc:
            return "Failed fecthing log dir %s from %s" % (server, dir)

        for log in logs.stdout.split():
            destination_log_filename = "%s-%s-%s" % (server, dir.strip('/').split('/')[-1], log)
            self.fetch_log(server, "%s/%s" % (dir, log), destination_log_filename)

        return None

    def fetch_chroma_diagnostics(self, server):
        """
        Collect the chroma diagnostics from the target
        :return: empty list on success or list of error messages that can be used for diagnosing what went wrong.
        """

        # Check that chroma-diagnostics is installed. May not be if installation failed, etc.
        if Shell.run(['ssh', server, 'which chroma-diagnostics']).rc:
            return["chroma-diagnostics not installed on %s. skipping." % server]

        # Generate the diagnostics from the server
        result = Shell.run(['ssh', server, 'chroma-diagnostics', '-v', '-v', '-v'])

        if result.timeout:
            return["Chroma Diagnostics timed-out"]

        # Find the diagnostics filename from the chroma-diagnostics output
        cd_out = result.stderr.decode('utf8')
        match = re.compile('/var/log/(diagnostics_.*\.tar\..*)').search(cd_out)
        if not match:
            return ["Did not find diagnostics filepath in chroma-diagnostics output:\nstderr:\n%s\nstdout:\n%s" %
                    (cd_out, result.stdout.decode('utf8'))]
        diagnostics = match.group(1).strip()

        errors = []

        # Copy and expand the diagnostics locally, so they will be able to be read in browser in Jenkins.
        errors.append(self.fetch_log(server, "/var/log/%s" % diagnostics, ''))
        errors.append(self.fetch_log(server, "chroma-diagnostics.log", '%s-chroma-diagnostics.log' % server))

        if diagnostics.endswith('tar.lzma'):
            if Shell.run(['tar', '--lzma', '-xvf', "%s/%s" % (self.destination_path, diagnostics),
                               '-C', self.destination_path]).rc:
                errors.append("Error tar --lzma the chroma diagnostics file")
        elif diagnostics.endswith('tar.gz'):
            if Shell.run(['tar', '-xvzf', "%s/%s" % (self.destination_path, diagnostics),
                               '-C', self.destination_path]).rc:
                errors.append("Error tar -xvzf the chroma diagnostics file")
        else:
            errors = "Didn't recognize chroma-diagnostics file format"

        if Shell.run(['rm', '-f', "%s/%s" % (self.destination_path, diagnostics)]).rc:
            errors.append("Unable to remove the diagnostics %s/%s" % (self.destination_path, diagnostics))

        return errors

if __name__ == '__main__':

    destination_path = sys.argv[1]
    cluster_cfg_path = sys.argv[2]

    Shell.run(['mkdir', '-p', destination_path])
    Shell.run(['rm', '-f', "%s.tgz" % destination_path])
    cluster_cfg_json = open(cluster_cfg_path)
    cluster_cfg = json.loads(cluster_cfg_json.read())

    chroma_managers = []
    for chroma_manager in cluster_cfg['chroma_managers']:
        chroma_managers.append("root@%s" % chroma_manager['address'])

    lustre_servers = []
    for lustre_server in cluster_cfg['lustre_servers']:
        if not lustre_server['distro'] == 'mock':
            lustre_servers.append("root@%s" % lustre_server['address'])

    test_runners = []
    for test_runner in cluster_cfg['test_runners']:
        test_runners.append("root@%s" % test_runner['address'])

    log_collector = ChromaLogCollector(destination_path, chroma_managers, lustre_servers, test_runners)
    errors = log_collector.collect_logs()

    if errors:
        print '\n'.join(errors)
        sys.exit(1)
