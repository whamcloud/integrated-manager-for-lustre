import uuid
import re
from collections import defaultdict
from tastypie.serializers import Serializer
import mock
import json

from chroma_core.models import ManagedHost
from chroma_core.models import ManagedTarget
from chroma_api.authentication import CsrfAuthentication
from chroma_core.services.job_scheduler import job_scheduler_notify
from chroma_core.services.job_scheduler.disabled_connection import DISABLED_CONNECTION
from emf_common.lib.agent_rpc import agent_result, agent_result_ok
from synthentic_objects import synthetic_lnet_configuration
from synthentic_objects import create_synthetic_device_info
from chroma_core.services.log import log_register
from tests.unit.chroma_core.helpers.test_api_client import TestApiClient
from tests.unit.chroma_core.helpers import helper
from emf_common.lib.date_time import EMFDateTime

log = log_register("mock_agent_rpc")


class MockAgentRpc(object):
    mock_servers = {}
    calls = []
    host_calls = defaultdict(list)

    @classmethod
    def start(cls):
        pass

    @classmethod
    def shutdown(cls):
        pass

    @classmethod
    def await_restart(cls, fqdn, timeout, old_session_id=None):
        pass

    @classmethod
    def await_session(cls, fqdn, timeout):
        return True

    @classmethod
    def get_session_id(cls, fqdn):
        return sum(bytearray(str(fqdn)))

    @classmethod
    def clear_calls(cls):
        cls.calls = []

    @classmethod
    def last_call(cls):
        return cls.calls[-1]

    @classmethod
    def skip_calls(cls, cmds_to_skip):
        """ Find the most recent agent RPC that wasn't in the list of specified cmds """
        index = 1

        while cls.calls[-index][0] in cmds_to_skip:
            index += 1

        return cls.calls[-index]

    succeed = True
    fail_commands = []
    selinux_enabled = False
    version = None
    capabilities = ["manage_targets"]

    @classmethod
    def remove(cls, fqdn):
        pass

    @classmethod
    def _fail(cls, fqdn):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        log.error("Synthetic agent error on host %s" % fqdn)
        raise AgentException(fqdn, "cmd", {"foo": "bar"}, "Fake backtrace")

    @classmethod
    def call(cls, fqdn, cmd, args, cancel_event):
        import django.db

        # If the DB was disabled for the Step within which we're run, we need to re-enable
        # DB access temporarily to run the mock agent ops
        db_disabled = django.db.connection.connection == DISABLED_CONNECTION
        try:
            if db_disabled:
                django.db.connection.connection = None

            from chroma_core.services.job_scheduler.agent_rpc import ActionInFlight

            host = ManagedHost.objects.get(fqdn=fqdn)
            result = cls._call(host, cmd, args)
            action_state = ActionInFlight("foo", fqdn, cmd, args)
            action_state.subprocesses = []
            return result, action_state
        finally:
            if db_disabled:
                django.db.connection.connection = DISABLED_CONNECTION

    @classmethod
    def _call(cls, host, cmd, args):
        cls.calls.append((cmd, args))
        cls.host_calls[host.fqdn].append((cmd, args))

        if not cls.succeed:
            cls._fail(host.fqdn)

        if (cmd, args) in cls.fail_commands:
            cls._fail(host.fqdn)

        mock_server = cls.mock_servers[host.address]

        log.info("invoke_agent %s %s %s" % (host, cmd, args))

        # This isn't really accurate because lnet is scanned asynchonously, but it is as close as we can get today
        # Fixme: Also I know think this is writing to the wrong thing and should be changing the mock_server entries.
        # to lnet_up, I guess the mock_server needs an lnet state really, rather than relying on nids present.
        if cmd == "load_lnet":
            synthetic_lnet_configuration(host, mock_server["nids"])
            return
        elif cmd == "device_plugin":
            # Only returns nid info today.
            return create_synthetic_device_info(host, mock_server, args["plugin"])
        elif cmd == "format_target":
            inode_size = None
            if "mkfsoptions" in args:
                inode_arg = re.search("-I (\d+)", args["mkfsoptions"])
                if inode_arg:
                    inode_size = int(inode_arg.group(1).__str__())

            if inode_size is None:
                # A 'foo' value
                inode_size = 777

            return {
                "uuid": uuid.uuid1().__str__(),
                "inode_count": 666,
                "inode_size": inode_size,
                "filesystem_type": "ext4",
            }
        elif cmd == "stop_target":
            ha_label = args["ha_label"]
            target = ManagedTarget.objects.get(ha_label=ha_label)
            return agent_result_ok
        elif cmd == "start_target":
            ha_label = args["ha_label"]
            target = ManagedTarget.objects.get(ha_label=ha_label)
            return agent_result(target.primary_host.nodename)
        elif cmd == "register_target":
            # Assume mount paths are "/mnt/testfs-OST0001" style
            mount_point = args["mount_point"]
            label = re.search("/mnt/([^\s]+)", mount_point).group(1)
            return {"label": label}
        elif cmd == "detect_scan":
            return mock_server["detect-scan"]
        elif cmd == "install_packages":
            return agent_result([])
        elif cmd == "register_server":
            api_client = TestApiClient()
            old_is_authenticated = CsrfAuthentication.is_authenticated
            try:
                CsrfAuthentication.is_authenticated = mock.Mock(return_value=True)
                api_client.client.login(username="debug", password="chr0m4_d3bug")
                fqdn = cls.mock_servers[host]["fqdn"]

                response = api_client.post(
                    args["url"] + "register/%s/" % args["secret"],
                    data={
                        "address": host,
                        "fqdn": fqdn,
                        "nodename": cls.mock_servers[host]["nodename"],
                        "capabilities": ["manage_targets"],
                        "version": cls.version,
                        "csr": helper.generate_csr(fqdn),
                    },
                )
                assert response.status_code == 201
                registration_data = Serializer().deserialize(response.content, format=response["Content-Type"])
                print("MockAgent.invoke returning %s" % registration_data)
                return registration_data
            finally:
                CsrfAuthentication.is_authenticated = old_is_authenticated
        elif cmd == "kernel_status":
            return {"running": "fake_kernel-0.1", "required": "fake_kernel-0.1", "available": ["fake_kernel-0.1"]}
        elif cmd == "selinux_status":
            return {"status": "Disabled"}
        elif cmd == "reboot_server":
            now = EMFDateTime.utcnow()
            log.info("rebooting %s; updating boot_time to %s" % (host, now))
            job_scheduler_notify.notify(host, now, {"boot_time": now})
        elif cmd == "which zfs":
            return 1
        elif "import platform;" in cmd:
            return "0"
        elif "socket.gethostbyname(socket.gethostname())" in cmd:
            if not mock_server["tests"]["hostname_valid"]:
                return "127.0.0.1"
            else:
                return mock_server["address"]
        elif "print os.uname()[1]" in cmd:
            return "%s\n%s" % (mock_server["nodename"], mock_server["fqdn"])
        elif "socket.getfqdn()" in cmd:
            return mock_server["fqdn"]
        elif "ping" in cmd:
            result = (0 if mock_server["tests"]["reverse_resolve"] else 2) + (
                0 if mock_server["tests"]["reverse_ping"] else 1
            )
            return result
        elif "ElectricFence" in cmd:
            return 0 if mock_server["tests"]["yum_can_update"] else 1
        elif "openssl version -a" in cmd:
            return 0 if mock_server["tests"]["openssl"] else 1
        elif "curl -k https" in cmd:
            return json.dumps({"host_id": host.id, "command_id": 0})
        elif cmd in [
            "configure_pacemaker",
            "unconfigure_pacemaker",
            "configure_target_store",
            "unconfigure_target_store",
            "deregister_server",
            "restart_agent",
            "shutdown_server",
            "host_corosync_config",
            "check_block_device",
            "set_conf_param",
            "purge_configuration",
        ]:
            return None
        elif cmd in [
            "configure_target_ha",
            "unconfigure_target_ha",
            "start_lnet",
            "stop_lnet",
            "unload_lnet",
            "unconfigure_lnet",
            "configure_corosync",
            "unconfigure_corosync",
            "start_corosync",
            "stop_corosync",
            "start_pacemaker",
            "stop_pacemaker",
            "configure_ntp",
            "unconfigure_ntp",
            "import_target",
            "export_target",
            "set_profile",
            "update_profile",
            "failover_target",
            "configure_network",
        ]:
            return agent_result_ok
        elif cmd == "get_corosync_autoconfig":
            return agent_result(
                {
                    "interfaces": {
                        "eth0": {"dedicated": False, "ipaddr": "192.168.0.1", "prefix": 24},
                        "eth1": {"dedicated": True, "ipaddr": "10.10.0.01", "prefix": 24},
                    },
                    "mcast_port": "666",
                }
            )
        else:
            assert False, (
                "The %s command is not in the known list for MockAgentRpc. Please add it then when people modify it a simple text search will let them know to change it here as well."
                % cmd
            )
