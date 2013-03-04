
import time

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.core.constants import TEST_TIMEOUT


class TestShutdownAndReboot(ChromaIntegrationTestCase):
    def _wait_for_server_boot_time(self, fqdn, old_boot_time=None):
        import dateutil.parser

        running_time = 0
        while running_time < TEST_TIMEOUT:
            hosts = self.get_list("/api/host/")
            for host in hosts:
                if host['fqdn'] == fqdn:
                    if host['boot_time'] is not None:
                        boot_time = dateutil.parser.parse(host['boot_time'])
                        if old_boot_time:
                            if boot_time > old_boot_time:
                                return boot_time
                        else:
                            return boot_time

            running_time += 1
            time.sleep(1)

        self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for host boot_time to be set.")

    def test_server_shutdown(self):
        # Signal to the harness that we're expecting a node to be down
        # after this test completes.
        self.down_node_expected = True

        server = config['lustre_servers'][0]
        self.add_hosts([server['address']])

        host = self.get_list("/api/host/")[0]

        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'ShutdownHostJob', 'args': {'host_id': host['id']}}],
            'message': "Test shutdown of %s" % server['fqdn']
        }).json

        self.wait_for_command(self.chroma_manager, command['id'])

        running_time = 0
        while running_time < TEST_TIMEOUT:
            if not self.remote_operations.host_contactable(server['address']):
                break

            running_time += 1
            time.sleep(1)

        self.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for host to shut down.")

    def test_server_reboot(self):
        server = config['lustre_servers'][0]
        self.add_hosts([server['address']])

        first_boot_time = self._wait_for_server_boot_time(server['fqdn'])
        host_id = self.get_list("/api/host/")[0]['id']

        command = self.chroma_manager.post("/api/command/", body = {
            'jobs': [{'class_name': 'RebootHostJob', 'args': {'host_id': host_id}}],
            'message': "Test reboot of %s" % server['fqdn']
        }).json

        self.wait_for_command(self.chroma_manager, command['id'])
        self.remote_operations.await_server_boot(server['fqdn'], restart = False)
        second_boot_time = self._wait_for_server_boot_time(server['fqdn'], first_boot_time)

        self.assertGreater(second_boot_time, first_boot_time)
