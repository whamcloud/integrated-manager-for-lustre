#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
#
# Simple script to gather all of the relevant logs from a cluster.
#
# Usage: ./chroma_log_collection.py destination_path cluster_cfg_host_machine:cluster_cfg_path
#   destination_path - the directory to copy all of the log files into
#   cluster_cfg_host_machine - the machine that has the cluster configuration file that describes the cluster to copy logs from.
#   cluster_cfg_path - the path to the cluster config file on the cluster_cfg_host_machine
#
# Ex usage: ./chroma_log_collection.py ss_log_collection_test some_machine:~/cluster_cfg.json

import json
import subprocess
import sys


class ChromaLogCollector(object):

    def __init__(self, destination_path, chroma_managers, lustre_servers, *args, **kwargs):
        super(ChromaLogCollector, self).__init__(*args, **kwargs)
        self.destination_path = destination_path
        self.chroma_managers = chroma_managers
        self.lustre_servers = lustre_servers

    def collect_logs(self):
        subprocess.call(['rm', '-rf', "%s/*.log" % destination_path])

        for chroma_manager in self.chroma_managers:
            logs = subprocess.check_output(['ssh', chroma_manager, 'ls /var/log/chroma/*.log | xargs -n1 basename'])
            for log in logs.split():
                self.fetch_log(chroma_manager, '/var/log/chroma/%s' % log, "%s-%s" % (chroma_manager, log))
            self.fetch_log(chroma_manager, '/var/log/messages', '%s-messages.log' % chroma_manager)

        for lustre_server in self.lustre_servers:
            self.fetch_log(lustre_server, '/var/log/chroma-agent.log', '%s-chroma-agent.log' % lustre_server)
            self.fetch_log(lustre_server, '/var/log/messages', '%s-messages.log' % lustre_server)
            self.fetch_pacemaker_configuration(lustre_server)

    def fetch_log(self, source_address, source_log_path, destination_log_filename):
        #print "Fetching %s from %s to %s/%s" % (source_log_path, source_address, self.destination_path, destination_log_filename)
        subprocess.check_call(['scp', "%s:%s" % (source_address, source_log_path), "%s/%s" % (self.destination_path, destination_log_filename)])

    def fetch_pacemaker_configuration(self, lustre_server):
        # Only attempt to fetch if pacemaker exists on the lustre server
        which_crm_exit_code = subprocess.call(['ssh', lustre_server, 'which crm'])
        if which_crm_exit_code == 0:
            crm_status = subprocess.check_output(['ssh', lustre_server, 'crm status'])
            f = open('%s/%s-crm-status.log' % (self.destination_path, lustre_server), 'w')
            f.write(crm_status)

            crm_configuration = subprocess.check_output(['ssh', lustre_server, 'crm configure show'])
            f = open('%s/%s-crm-configuration.log' % (self.destination_path, lustre_server), 'w')
            f.write(crm_configuration)


if __name__ == '__main__':

    destination_path = sys.argv[1]
    cluster_cfg_host_machine, cluster_cfg_path = sys.argv[2].split(':')

    subprocess.call(['mkdir', '-p', destination_path])
    subprocess.call(['rm', '-f', '%s.tgz' % destination_path])
    subprocess.call(['rm', '-f', '%s/cluster_cfg.json' % destination_path])
    subprocess.check_call(['scp', "%s:%s" % (cluster_cfg_host_machine, cluster_cfg_path), "%s/cluster_cfg.json" % destination_path])
    cluster_cfg_json = open('%s/cluster_cfg.json' % destination_path)
    cluster_cfg = json.loads(cluster_cfg_json.read())

    chroma_managers = []
    for chroma_manager in cluster_cfg['chroma_managers']:
        chroma_managers.append(chroma_manager['address'])

    lustre_servers = []
    for lustre_server in cluster_cfg['lustre_servers']:
        lustre_servers.append(lustre_server['address'])

    log_collector = ChromaLogCollector(destination_path, chroma_managers, lustre_servers)
    log_collector.collect_logs()
    subprocess.call(['tar', '-czf', '%s.tgz' % destination_path, destination_path])
