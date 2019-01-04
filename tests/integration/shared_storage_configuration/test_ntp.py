import datetime


from testconfig import config
from django.utils.unittest.case import skip

from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


class TestNtpSync(ChromaIntegrationTestCase):
    NTP_SYNC_PERIOD = 30
    TIME_OFFSET_HOURS = 8
    TIME_ERROR_LARGE_MINS = 5
    TIME_ERROR_SMALL_MINS = 1

    def _change_agent_time(self):
        """ Modify agent time to be different from the manager time """

        manager_dt = self.remote_operations.get_server_time(self.manager_address)

        # Calculate incorrect time to set on agent host
        new_agent_dt = manager_dt + datetime.timedelta(hours=self.TIME_OFFSET_HOURS)

        self.remote_operations.set_server_time(self.agent_address, new_agent_dt)

        agent_dt = self.remote_operations.get_server_time(self.agent_address)

        # Verify agent time has been set to near desired value
        assert self.remote_operations.check_time_within_range(
            agent_dt, new_agent_dt, minutes=self.TIME_ERROR_LARGE_MINS
        )

    def _check_agent_time(self):
        """ Check agent time has been synchronised with manager time """

        manager_dt = self.remote_operations.get_server_time(self.manager_address)
        agent_dt = self.remote_operations.get_server_time(self.agent_address)

        return self.remote_operations.check_time_within_range(agent_dt, manager_dt, minutes=self.TIME_ERROR_SMALL_MINS)

    @skip("HYD-6534 causes this to fail")
    def test_ntp_sync(self):
        """ Test agent time synchronised with manager """

        self.manager_address = config["chroma_managers"][0]["address"]
        self.manager_fqdn = config["chroma_managers"][0]["fqdn"]
        self.agent_address = self.TEST_SERVERS[0]["address"]

        # Now agent is now out of sync with manager, add host (implicitly configuring ntp)
        self.add_hosts([self.agent_address])

        self.wait_until_true(
            self._check_agent_time,
            error_message="agent time not synchronised with manager after add",
            timeout=self.NTP_SYNC_PERIOD,
        )

        # Now test time synchronisation if un/configure_ntp is called through agent cli
        self.remote_operations._ssh_address(self.agent_address, "chroma-agent unconfigure_ntp")

        self._change_agent_time()

        self.assertFalse(self._check_agent_time())

        # Now agent is now out of sync with manager, configure ntp
        self.remote_operations._ssh_address(
            self.agent_address, "chroma-agent configure_ntp --ntp_server %s" % self.manager_fqdn
        )

        self.wait_until_true(
            self._check_agent_time,
            error_message="agent time not synchronised with manager after configure_ntp()",
            timeout=self.NTP_SYNC_PERIOD,
        )
