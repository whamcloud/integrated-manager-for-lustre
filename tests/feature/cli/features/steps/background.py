import uuid
import os
import json
from collections import defaultdict

from nose.tools import *


def load_filesystem_from_json(data):
    # Since this is only ever used for the behave tests, and the behave tests
    # are slated to be decommissioned at some point, we're just going to
    # abandon all pretense that we might be loading a non-synthetic cluster.
    from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
    from tests.unit.chroma_core.helpers import synthetic_volume
    from chroma_core.models import ManagedMgs, VolumeNode

    from chroma_core.lib.cache import ObjectCache
    from chroma_core.models import ManagedHost, ManagedTarget, ManagedTargetMount
    from chroma_core.models import Nid
    from tests.unit.chroma_core.helpers import synthetic_host

    lookup = defaultdict(dict)

    for host_info in data["hosts"]:
        from tests.unit.chroma_core.helpers import MockAgentRpc

        mock_host_info = MockAgentRpc.mock_servers[host_info["address"]]
        # host, command = JobSchedulerClient.create_host(mock_host_info['fqdn'], mock_host_info['nodename'], ['manage_targets'], address = host_info['address'])
        nids = [Nid.split_nid_string(n) for n in mock_host_info["nids"]]

        # update mock_servers with list of Nid objects
        MockAgentRpc.mock_servers[host_info["address"]]["nids"] = nids

        host = synthetic_host(
            mock_host_info["address"], nids=nids, fqdn=mock_host_info["fqdn"], nodename=mock_host_info["nodename"]
        )
        ObjectCache.add(ManagedHost, host)
        host.state = "managed"
        host.save()
        lookup["hosts"][host_info["address"]] = host

    def _create_volume_for_mounts(mounts):
        # The test data doesn't give us a serial, so mung one out of the device paths
        # on the basis that they're iSCSI-style
        serial = mounts[0]["device_node"].split("/")[-1]
        volume = synthetic_volume(serial=serial)
        for mount in mounts:
            VolumeNode.objects.create(
                host=lookup["hosts"][mount["host"]], path=mount["device_node"], primary=mount["primary"], volume=volume
            )
        return volume

    for mgs_info in data["mgss"]:
        volume = _create_volume_for_mounts(mgs_info["mounts"])
        target, target_mounts = ManagedMgs.create_for_volume(volume.id)
        target.uuid = uuid.uuid4().__str__()
        target.ha_label = "%s_%s" % (target.name, uuid.uuid4().__str__()[0:6])
        ObjectCache.add(ManagedTarget, target.managedtarget_ptr)
        for tm in target_mounts:
            ObjectCache.add(ManagedTargetMount, tm)
        lookup["mgt"][mgs_info["mounts"][0]["host"]] = target

    for fs_info in data["filesystems"]:
        fs_bundle = {
            "name": fs_info["name"],
            "mgt": {"id": lookup["mgt"][fs_info["mgs"]].id},
            "mdts": [],
            "osts": [],
            "conf_params": {},
        }

        for mdt_info in fs_info["mdts"]:
            volume = _create_volume_for_mounts(mdt_info["mounts"])

            # Although we create multiple volumes for the mdt, initially only add a single volume, once delete of MDT
            # is possible we can add them all and then delete before adding. This code is structured for that fixed case.
            if not fs_bundle["mdts"]:
                fs_bundle["mdts"].append({"volume_id": volume.id, "conf_params": {}})

        for ost_info in fs_info["osts"]:
            volume = _create_volume_for_mounts(ost_info["mounts"])
            fs_bundle["osts"].append({"volume_id": volume.id, "conf_params": {}})

        fs, command = JobSchedulerClient.create_filesystem(fs_bundle)


@given('the "{sample_name}" data is loaded')
def step(context, sample_name):
    from tests.unit.chroma_core.helpers import MockAgentRpc

    from chroma_core.models.filesystem import ManagedFilesystem

    # Don't reload all of this if a previous scenario set it up
    # and it hasn't been torn down again.
    if ManagedFilesystem.objects.count() > 0:
        return

    path = os.path.join(os.path.dirname(__file__), "../../../../sample_data/%s.json" % sample_name)
    with open(path) as fh:
        data = json.load(fh)

    MockAgentRpc.mock_servers = dict([[h["address"], h] for h in data["hosts"]])
    load_filesystem_from_json(data)

    from chroma_core.models.host import Volume

    # We need to do this in order to generate the labels, apparently.
    for volume in Volume.objects.all():
        volume.save()

    from chroma_core.models.host import ManagedHost

    eq_(ManagedHost.objects.count(), len(MockAgentRpc.mock_servers.keys()))


@given('the "{name}" mocks are loaded')
def step(context, name):
    import os
    import json
    from chroma_core.models import Nid
    from tests.unit.chroma_core.helpers import MockAgentRpc

    # Skip setup if it was already done in a previous scenario.
    if len(MockAgentRpc.mock_servers) > 0:
        return

    path = os.path.join(os.path.dirname(__file__), "../../../../sample_data/%s.json" % name)
    with open(path) as fh:
        data = json.load(fh)

    for host in data["hosts"]:
        host["nids"] = [Nid.split_nid_string(n) for n in host["nids"]]
        MockAgentRpc.mock_servers[host["address"]] = host


@given("the mock servers are set up")
def step(context):
    from chroma_core.models.host import ManagedHost, VolumeNode
    from tests.unit.chroma_core.helpers import MockAgentRpc, synthetic_host, synthetic_volume_full

    for address, host_info in sorted(MockAgentRpc.mock_servers.items()):
        if not ManagedHost.objects.filter(fqdn=host_info["fqdn"]).exists():
            host = synthetic_host(
                address, nids=host_info["nids"], fqdn=host_info["fqdn"], nodename=host_info["nodename"]
            )

    for address, host_info in sorted(MockAgentRpc.mock_servers.items()):
        if not VolumeNode.objects.filter(host__fqdn=host_info["fqdn"], path__startswith="/fake/path/").exists():
            synthetic_volume_full(ManagedHost.objects.get(fqdn=host_info["fqdn"]))

    eq_(ManagedHost.objects.count(), len(MockAgentRpc.mock_servers))


@given("the config has been reset to defaults")
def step(context):
    from chroma_cli.config import Configuration
    from chroma_cli.defaults import defaults

    context.cli_config = Configuration()
    context.cli_config.update(defaults)
