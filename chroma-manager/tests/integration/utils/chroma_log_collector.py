#
# Simple script to gather all of the relevant logs from a cluster.
#
# Usage: ./chroma_log_collection.py destination_path cluster_cfg_path
#   destination_path - the directory to copy all of the log files into
#   cluster_cfg_path - the path to the cluster config file
#
# Ex usage: ./chroma_log_collection.py ss_log_collection_test some_machine:~/cluster_cfg.json

import json
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
            self.fetch_log(test_runner, '/var/log/messages', '%s-messages.log' % test_runner)

        for chroma_manager in self.chroma_managers:
            self.fetch_log_dir(chroma_manager, '/var/log/chroma/')
            self.fetch_log(chroma_manager, '/var/log/messages', '%s-messages.log' % chroma_manager)
            self.fetch_log_dir(chroma_manager, '/var/log/httpd/')
            self.fetch_log(chroma_manager, '/var/log/yum.log', '%s-yum.log' % chroma_manager)

        for lustre_server in self.lustre_servers:
            self.fetch_log(lustre_server, '/var/log/chroma-agent-console.log', '%s-chroma-agent-console.log' % lustre_server)
            self.fetch_log(lustre_server, '/var/log/chroma-agent.log', '%s-chroma-agent.log' % lustre_server)
            self.fetch_log(lustre_server, '/var/log/messages', '%s-messages.log' % lustre_server)
            self.fetch_log(lustre_server, '/var/log/yum.log', '%s-yum.log' % lustre_server)
            self.fetch_pacemaker_configuration(lustre_server)

    def fetch_log(self, server, source_log_path, destination_log_filename):
        print "Fetching %s from %s to %s/%s" % (source_log_path, server, self.destination_path, destination_log_filename)
        subprocess.call(['scp', "%s:%s" % (server, source_log_path), "%s/%s" % (self.destination_path, destination_log_filename)])

    def fetch_log_dir(self, server, dir):
        logs = subprocess.Popen(['ssh', server, "ls %s | xargs -n1 basename" % dir], stdout=subprocess.PIPE).communicate()[0]
        for log in logs.split():
            destination_log_filename = "%s-%s-%s" % (server, dir.strip('/').split('/')[-1], log)
            self.fetch_log(server, '%s/%s' % (dir, log), destination_log_filename)

    def fetch_pacemaker_configuration(self, lustre_server):
        # Only attempt to fetch if pacemaker exists on the lustre server
        if subprocess.call(['ssh', lustre_server, 'which pcs']) == 0:
            pcs_status = subprocess.Popen(['ssh', lustre_server, 'pcs status'], stdout=subprocess.PIPE).communicate()[0]
            f = open('%s/%s-pcs-status.log' % (self.destination_path, lustre_server), 'w')
            try:
                f.write(pcs_status)
            finally:
                f.close()

            pcs_configuration = subprocess.Popen(['ssh', lustre_server, 'pcs config'], stdout=subprocess.PIPE).communicate()[0]
            f = open('%s/%s-pcs-configuration.log' % (self.destination_path, lustre_server), 'w')
            try:
                f.write(pcs_configuration)
            finally:
                f.close()


if __name__ == '__main__':

    destination_path = sys.argv[1]
    cluster_cfg_path = sys.argv[2]

    subprocess.call(['mkdir', '-p', destination_path])
    subprocess.call(['rm', '-f', '%s.tgz' % destination_path])
    cluster_cfg_json = open(cluster_cfg_path)
    cluster_cfg = json.loads(cluster_cfg_json.read())

    chroma_managers = []
    for chroma_manager in cluster_cfg['chroma_managers']:
        chroma_managers.append("root@%s" % chroma_manager['address'])

    lustre_servers = []
    for lustre_server in cluster_cfg['lustre_servers']:
        if not lustre_server['distro'] == "mock":
            lustre_servers.append("root@%s" % lustre_server['address'])

    test_runners = []
    for test_runner in cluster_cfg['test_runners']:
        test_runners.append("root@%s" % test_runner['address'])

    log_collector = ChromaLogCollector(destination_path, chroma_managers, lustre_servers, test_runners)
    log_collector.collect_logs()
    subprocess.call(['tar', '-czf', '%s.tgz' % destination_path, destination_path])
