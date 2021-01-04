import mock

from chroma_core.models import Volume, VolumeNode, ManagedHost, LNetConfiguration
from chroma_core.models import NetworkInterface, Nid, ServerProfile
from chroma_core.models import NTPConfiguration
from chroma_core.models import CorosyncConfiguration
from chroma_core.models import PacemakerConfiguration
from chroma_core.models import Command
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import StorageResourceRecord
from chroma_core.services.log import log_register
from tests.unit.chroma_core.helpers.helper import random_str

log = log_register("synthetic_objects")


def synthetic_volume(serial=None, with_storage=True, usable_for_lustre=True):
    """
    Create a Volume and an underlying StorageResourceRecord
    """
    volume = Volume.objects.create()

    if not serial:
        serial = "foobar%d" % volume.id

    attrs = {"serial": serial, "size": 8192000}

    if with_storage:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class("linux", "ScsiDevice")

        storage_resource, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)

        volume.storage_resource = storage_resource

    volume.usable_for_lustre = usable_for_lustre

    volume.save()

    return volume


def synthetic_volume_full(primary_host, secondary_hosts=None, usable_for_lustre=True):
    """
    Create a Volume and some VolumeNodes
    """
    secondary_hosts = [] if secondary_hosts is None else secondary_hosts

    volume = synthetic_volume(usable_for_lustre=usable_for_lustre)
    path = "/fake/path/%s" % volume.id

    VolumeNode.objects.create(volume=volume, host=primary_host, path=path, primary=True)

    for host in secondary_hosts:
        VolumeNode.objects.create(volume=volume, host=host, path=path, primary=False)

    return volume


def synthetic_host(
    address=None, nids=list([]), storage_resource=False, fqdn=None, nodename=None, server_profile="test_profile"
):
    """
    Create a ManagedHost + paraphernalia, with states set as if configuration happened successfully

    :param storage_resource: If true, create a PluginAgentResources (additional overhead, only sometimes required)
    """

    server_profile = ServerProfile.objects.get(name=server_profile)

    if address is None:
        address = random_str(postfix=".tld")

    if fqdn is None:
        fqdn = address
    if nodename is None:
        nodename = address

    host = ManagedHost.objects.create(
        address=address,
        fqdn=fqdn,
        nodename=nodename,
        state="managed",
        server_profile=server_profile,
        immutable_state=not server_profile.managed if server_profile else False,
    )

    ObjectCache.add(ManagedHost, host)

    lnet_configuration = synthetic_lnet_configuration(host, nids)

    if server_profile.managed:
        synthetic_ntp_configuration(host)
        synthetic_corosync_configuration(host)
        synthetic_pacemaker_configuration(host)

    if storage_resource:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
            "linux", "PluginAgentResources"
        )
        StorageResourceRecord.get_or_create_root(
            resource_class, resource_class_id, {"plugin_name": "linux", "host_id": host.id}
        )

    return host


def synthetic_lnet_configuration(host, nids):
    lnet_configuration, _ = LNetConfiguration.objects.get_or_create(host=host)

    ObjectCache.add(LNetConfiguration, lnet_configuration)

    # Now delete any existing nids as we will recreate them if some have been requested.
    Nid.objects.filter(lnet_configuration=lnet_configuration).delete()

    if nids:
        assert type(nids[0]) == Nid.Nid

        lnet_configuration.state = "lnet_up"

        interface_no = 0
        for nid in nids:
            try:
                network_interface = NetworkInterface.objects.get(
                    host=host, name="eth%s" % interface_no, type=nid.lnd_type
                )
                network_interface.inet4_address = nid.nid_address
                network_interface.inet4_prefix = 24
                network_interface.state_up = True
            except NetworkInterface.DoesNotExist:
                network_interface = NetworkInterface.objects.create(
                    host=host,
                    name="eth%s" % interface_no,
                    type=nid.lnd_type,
                    inet4_address=nid.nid_address,
                    inet4_prefix=24,
                    state_up=True,
                )

            network_interface.save()

            nid_record = Nid.objects.create(
                lnet_configuration=lnet_configuration,
                network_interface=network_interface,
                lnd_network=nid.lnd_network,
                lnd_type=nid.lnd_type,
            )
            nid_record.save()

            interface_no += 1
    else:
        lnet_configuration.state = "lnet_unloaded"

    lnet_configuration.save()

    return lnet_configuration


def create_synthetic_device_info(host, mock_server, plugin):
    """Creates the data returned from plugins for integration test purposes. Only does lnet data because
    at present that is all we need."""

    # Default is an empty dict.
    result = {}

    # First see if there is any explicit mocked data
    try:
        result = mock_server["device-plugin"][plugin]
    except KeyError:
        pass

    # This should come from the simulator, so I am adding to the state of this code.
    # It is a little inconsistent because network devices come and go as nids come and go.
    # really they should be consistent. But I am down to the wire on this and this preserves
    # the current testing correctly. So it is not a step backwards.
    if (plugin == "linux_network") and (result == {}):
        interfaces = {}
        nids = {}

        if host.state.startswith("lnet"):
            lnet_state = host.state
        else:
            lnet_state = "lnet_unloaded"

        mock_nids = mock_server["nids"]
        interface_no = 0
        if mock_nids:
            for nid in mock_nids:
                name = "eth%s" % interface_no
                interfaces[name] = {
                    "mac_address": "12:34:56:78:90:%s" % interface_no,
                    "inet4_address": nid.nid_address,
                    "inet6_address": "Need An inet6 Simulated Address",
                    "type": nid.lnd_type,
                    "rx_bytes": "24400222349",
                    "tx_bytes": "1789870413",
                    "up": True,
                }

                nids[name] = {
                    "nid_address": nid.nid_address,
                    "lnd_type": nid.lnd_type,
                    "lnd_network": nid.lnd_network,
                    "status": "?",
                    "refs": "?",
                    "peer": "?",
                    "rtr": "?",
                    "max": "?",
                    "tx": "?",
                    "min": "?",
                }

                interface_no += 1

        result = {"interfaces": interfaces, "lnet": {"state": lnet_state, "nids": nids}}

    return {plugin: result}


def _create_simple_synthetic_object(class_, **kwargs):
    synthetic_object = class_(**kwargs)
    synthetic_object.save()
    ObjectCache.add(class_, synthetic_object)

    return synthetic_object


def synthetic_ntp_configuration(host):
    assert host.ntp_configuration == None
    return _create_simple_synthetic_object(NTPConfiguration, host=host)


def synthetic_corosync_configuration(host):
    assert host.corosync_configuration == None
    return _create_simple_synthetic_object(CorosyncConfiguration, host=host)


def synthetic_pacemaker_configuration(host):
    assert host.pacemaker_configuration == None
    return _create_simple_synthetic_object(PacemakerConfiguration, host=host, state="started")


def parse_synthentic_device_info(host_id, data):
    """Parses the data returned from plugins for integration test purposes. On does lnet data because
    at present that is all we need."""

    # This creates nid tuples so it can use synthetic_host_create_lnet_configuration to do the
    # actual writes to the database
    for plugin, device_data in data.items():
        if plugin == "linux_network":
            if len(device_data["lnet"]["nids"]) > 0:
                nid_tuples = []

                for name, nid in device_data["lnet"]["nids"].items():
                    nid_tuples.append(Nid.Nid(nid["nid_address"], nid["lnd_type"], nid["lnd_network"]))
            else:
                nid_tuples = None

            synthetic_lnet_configuration(ManagedHost.objects.get(id=host_id), nid_tuples)


def _synthetic_create_host_ssh(address, server_profile, root_pw=None, pkey=None, pkey_pw=None):
    try:
        host = ManagedHost.objects.get(address=address)
        assert host.state == "undeployed"
    except ManagedHost.DoesNotExist:
        from tests.unit.chroma_core.helpers.mock_agent_rpc import MockAgentRpc

        host_info = MockAgentRpc.mock_servers[address]

        host = synthetic_host(
            address,
            fqdn=host_info["fqdn"],
            nids=host_info["nids"],
            nodename=host_info["nodename"],
            server_profile=server_profile,
        )

    command = Command.objects.create(message="No-op", complete=True)
    return host, command


create_host_ssh_patch = mock.patch(
    "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient.create_host_ssh",
    new=mock.Mock(side_effect=_synthetic_create_host_ssh),
)
