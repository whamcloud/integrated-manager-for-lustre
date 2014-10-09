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
import subprocess
import sys


class ChromaLogCollector(object):

    def __init__(self, destination_path, chroma_managers, lustre_servers, test_runners, *args, **kwargs):
        super(ChromaLogCollector, self).__init__(*args, **kwargs)
        self.destination_path = destination_path
        self.chroma_managers = chroma_managers
        self.lustre_servers = lustre_servers
        self.test_runners = test_runners

    def collect_logs(self):
        subprocess.call(['rm', '-rf', "%s/*.log" % destination_path])

        for test_runner in self.test_runners:
            self.fetch_log(test_runner, '/var/log/chroma_test.log', "%s-chroma_test.log" % test_runner)
            self.fetch_log(test_runner, '/var/log/messages', "%s-messages.log" % test_runner)

        for server in self.chroma_managers + self.lustre_servers:
            self.fetch_log(server, '/var/log/yum.log', "%s-yum.log" % server)
            self.fetch_chroma_diagnostics(server)

    def fetch_log(self, server, source_log_path, destination_log_filename):
        print "Fetching %s from %s to %s/%s" % (source_log_path, server, self.destination_path, destination_log_filename)
        subprocess.call(['scp', "%s:%s" % (server, source_log_path), "%s/%s" % (
            self.destination_path, destination_log_filename)])

    def fetch_log_dir(self, server, dir):
        logs = subprocess.Popen(['ssh', server, "ls %s | xargs -n1 basename" % dir], stdout=subprocess.PIPE).communicate()[0]
        for log in logs.split():
            destination_log_filename = "%s-%s-%s" % (server, dir.strip('/').split('/')[-1], log)
            self.fetch_log(server, "%s/%s" % (dir, log), destination_log_filename)

    def fetch_chroma_diagnostics(self, server):
        # Check that chroma-diagnostics is installed. May not be if installation failed, etc.
        if not subprocess.call(['ssh', server, 'which chroma-diagnostics']) == 0:
            print "chroma-diagnostics not installed on %s. skipping." % server
            return

        # Generate the diagnostics from the server
        pipe = subprocess.Popen(['ssh', server, 'chroma-diagnostics'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        # Find the diagnostics filename from the chroma-diagnostics output
        cd_out = ''.join([x.decode('utf8') for x in pipe.stderr.readlines()])
        match = re.compile('/var/log/(.*)').search(cd_out)
        if not match:
            print "Did not find diagnostics filepath in chroma-diagnostics output"
            sys.exit(1)
        diagnostics = match.group(1).strip()

        # Copy and expand the diagnostics locally, so they will be able to be read in browser in Jenkins.
        self.fetch_log(server, "/var/log/%s" % diagnostics, '')
        self.fetch_log(server, "chroma-diagnostics.log", '%s-chroma-diagnostics.log' % server)
        if diagnostics.endswith('tar.lzma'):
            subprocess.call(
                ['tar', '--lzma', '-xvf', "%s/%s" % (self.destination_path, diagnostics),
                    '-C', self.destination_path], stdout=subprocess.PIPE)
        elif diagnostics.endswith('tar.gz'):
            subprocess.call(
                ['tar', '-xvzf', "%s/%s" % (self.destination_path, diagnostics),
                    '-C', self.destination_path], stdout=subprocess.PIPE)
        else:
            print "Didnt recognize chroma-diagnostics file format"
            sys.exit(1)

        subprocess.call(['rm', '-f', "%s/%s" % (self.destination_path, diagnostics)],
                stdout=subprocess.PIPE)


if __name__ == '__main__':

    destination_path = sys.argv[1]
    cluster_cfg_path = sys.argv[2]

    subprocess.call(['mkdir', '-p', destination_path])
    subprocess.call(['rm', '-f', "%s.tgz" % destination_path])
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
    log_collector.collect_logs()
