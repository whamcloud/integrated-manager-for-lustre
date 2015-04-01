

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from django.utils.unittest import skipIf


class TestFirewall(ChromaIntegrationTestCase):
    TEST_SERVERS = config['lustre_servers'][0:4]

    @skipIf(config.get('simulator'), "Can't be simulated")
    def test_manager(self):
        """ Test that the manager has the required selinux setting and firewall access rules installed"""
        chroma_manager = config['chroma_managers'][0]

        contents = self.remote_operations.get_file_content(chroma_manager,
                                                           "/selinux/enforce")
        self.assertEqual(contents, "1")

        # TODO: refactor reset_cluster/reset_chroma_manager_db so that previous
        # state can be cleaned up without initializing the DB
        # then we can do a before/after firewall state comparison where
        # before and after are before chroma-config setup and after it
        found = 0
        # XXX: this assumes there is only one chroma manager
        for rule in self.remote_operations.get_iptables_rules(chroma_manager):
            if rule["target"] == "ACCEPT" and \
               rule["source"] == "0.0.0.0/0" and \
               rule["destination"] == "0.0.0.0/0" and \
               (rule["prot"] == "udp" or rule["prot"] == "tcp") and \
               ((rule["details"] == "state NEW udp dpt:123" and
                 chroma_manager.get('ntp_server', "localhost") ==
                 "localhost") or
               rule["details"] == "state NEW tcp dpt:80" or
               rule["details"] == "state NEW tcp dpt:443"):
                    found += 1

        if chroma_manager.get('ntp_server', "localhost") == "localhost":
            self.assertEqual(found, 3)
        else:
            self.assertEqual(found, 2)

    @skipIf(config.get('simulator'), "Can't be simulated")
    def test_agent(self):
        """Test that when hosts are added and a filesytem is created, that all required firewall accesses are installed"""

        for server in self.TEST_SERVERS:
            self.remote_operations.get_iptables_rules(server)

        self.assertGreaterEqual(len(self.TEST_SERVERS), 4)

        self.hosts = self.add_hosts([s['address'] for s in self.TEST_SERVERS])

        volumes = self.wait_for_shared_volumes(4, 4)

        mgt_volume = volumes[0]
        mdt_volume = volumes[1]
        ost1_volume = volumes[2]
        ost2_volume = volumes[3]
        self.set_volume_mounts(mgt_volume, self.hosts[0]['id'], self.hosts[1]['id'])
        self.set_volume_mounts(mdt_volume, self.hosts[1]['id'], self.hosts[0]['id'])
        self.set_volume_mounts(ost1_volume, self.hosts[2]['id'], self.hosts[3]['id'])
        self.set_volume_mounts(ost2_volume, self.hosts[3]['id'], self.hosts[2]['id'])

        self.filesystem_id = self.create_filesystem({
            'name': 'testfs',
            'mgt': {'volume_id': mgt_volume['id']},
            'mdts': [{
                'volume_id': mdt_volume['id'],
                'conf_params': {}

            }],
            'osts': [{
                'volume_id': ost1_volume['id'],
                'conf_params': {}
            }, {
                'volume_id': ost2_volume['id'],
                'conf_params': {}
            }],
            'conf_params': {}
        })

        mcastports = {}
        for server in self.TEST_SERVERS:

            contents = self.remote_operations.get_file_content(server,
                                                               "/selinux/enforce")
            self.assertEqual(contents, "")

            found = 0
            mcastport = self.remote_operations.get_corosync_port(server)
            self.assertIsNotNone(mcastport)

            mcastports[server['address']] = mcastport

            for rule in self.remote_operations.get_iptables_rules(server):
                if rule["target"] == "ACCEPT" and \
                   rule["source"] == "0.0.0.0/0" and \
                   rule["destination"] == "0.0.0.0/0" and \
                   (rule["prot"] == "udp" or rule["prot"] == "tcp") and \
                   (rule["details"] == "state NEW udp dpt:%s" % mcastport or
                   rule["details"] == "state NEW tcp dpt:988"):
                    found += 1

            self.assertEqual(found, 2)

        # tear it down and make sure firewall rules are cleaned up
        self.graceful_teardown(self.chroma_manager)
        found = 0
        for server in self.TEST_SERVERS:
            mcastport = mcastports[server['address']]
            for rule in self.remote_operations.get_iptables_rules(server):
                if rule["target"] == "ACCEPT" and \
                   rule["source"] == "0.0.0.0/0" and \
                   rule["destination"] == "0.0.0.0/0" and \
                   rule["prot"] == "udp" and \
                   rule["details"] == "state NEW udp dpt:%s" % mcastport:
                    found += 1

            self.assertEqual(found, 0)

            line = self.remote_operations.grep_file(server,
                                                    "--dport %s" % mcastport,
                                                    "/etc/sysconfig/iptables")
            self.assertEqual(line, "")

            line = self.remote_operations.grep_file(server,
                                                    "--port=%s" % mcastport,
                                                    "/etc/sysconfig/system-config-firewall")
            self.assertEqual(line, "")
