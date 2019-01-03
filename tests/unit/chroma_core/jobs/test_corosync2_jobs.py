import mock

from tests.unit.chroma_core.jobs.test_jobs import TestJobs, InvokeAgentInvoke
from chroma_core.models.corosync2 import AutoConfigureCorosyncStep


class TestCorosyncConfiguration(TestJobs):
    def test_acc_step(self):
        mcast_port = 55442
        prefix = 21
        eth0_ipaddr = "10.14.81.249"
        eth1_ipaddr = "10.128.1.249"

        mock_corosync_configuration = mock.MagicMock()
        mock_corosync_configuration.host.fqdn = "bob.monkhouse.show"
        mock_corosync_configuration.host.state = "packages_installed"

        mock_actioning_host = mock.MagicMock()
        mock_actioning_host.fqdn = "bruce.forsyth.show"
        mock_actioning_host.state = "packages_installed"

        mock.patch(
            "chroma_core.models.AutoConfigureCorosyncStep._corosync_peers", return_value=[mock_actioning_host.fqdn]
        ).start()

        mock.patch(
            "chroma_core.models.AutoConfigureCorosyncStep._create_pcs_password", return_value="vVGuFNrZ1YUhMDEv6MDe"
        ).start()

        mock_managed_hosts_objects = mock.MagicMock()
        mock_managed_hosts_objects.get = mock.MagicMock(return_value=mock_actioning_host)

        mock.patch("chroma_core.models.ManagedHost.objects", new=mock_managed_hosts_objects).start()

        mock.patch("chroma_core.services.job_scheduler.job_scheduler_notify.notify").start()

        self.add_invokes(
            InvokeAgentInvoke(
                mock_corosync_configuration.host.fqdn,
                "get_corosync_autoconfig",
                {},
                {
                    "mcast_port": mcast_port,
                    "interfaces": {
                        "eth1": {"dedicated": True, "ipaddr": eth1_ipaddr, "prefix": prefix},
                        "eth0": {"dedicated": False, "ipaddr": eth0_ipaddr, "prefix": prefix},
                    },
                },
                None,
            ),
            InvokeAgentInvoke(
                mock_corosync_configuration.host.fqdn,
                "configure_network",
                {"ring1_ipaddr": eth1_ipaddr, "ring1_name": "eth1", "ring0_name": "eth0", "ring1_prefix": prefix},
                None,
                None,
            ),
            InvokeAgentInvoke(
                mock_corosync_configuration.host.fqdn,
                "configure_corosync2_stage_1",
                {"mcast_port": mcast_port, "pcs_password": "vVGuFNrZ1YUhMDEv6MDe"},
                None,
                None,
            ),
            InvokeAgentInvoke(
                mock_actioning_host.fqdn,
                "configure_corosync2_stage_2",
                {
                    "ring1_name": "eth1",
                    "create_cluster": False,
                    "mcast_port": mcast_port,
                    "new_node_fqdn": mock_corosync_configuration.host.fqdn,
                    "ring0_name": "eth0",
                    "pcs_password": "vVGuFNrZ1YUhMDEv6MDe",
                },
                None,
                None,
            ),
        )

        acc_step = AutoConfigureCorosyncStep(
            self.mock_job, {"corosync_configuration": mock_corosync_configuration}, None, None, None
        )

        acc_step.run(acc_step.args)

        self.assertRanAllInvokesInOrder()

    def test_pcs_password(self):
        _pcs_passwords = []

        passwords_to_create = 1000

        for _ in range(0, passwords_to_create):
            new_password = AutoConfigureCorosyncStep._create_pcs_password()

            self.assertTrue(new_password not in _pcs_passwords)
            self.assertEqual(len(new_password), 20)

            _pcs_passwords.append(new_password)

        self.assertEqual(len(_pcs_passwords), passwords_to_create)

    def test_pcs_password_masked(self):
        def process_callback(pcs_password, console_output):
            self.assertFalse(pcs_password in console_output)

        acc_step = AutoConfigureCorosyncStep(
            self.mock_job,
            {},
            None,
            lambda console_output: process_callback(acc_step._pcs_password, console_output),
            None,
        )

        acc_step._console_callback("This contains the password here %s" % acc_step._pcs_password)
