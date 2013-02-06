#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
import json
from nose.tools import *
from behave import *
from tests.utils.load_config import load_string


@given('the "{sample_name}" data is loaded')
def step(context, sample_name):
    from tests.unit.chroma_core.helper import MockAgentRpc

    from chroma_core.models.filesystem import ManagedFilesystem
    # Don't reload all of this if a previous scenario set it up
    # and it hasn't been torn down again.
    if ManagedFilesystem.objects.count() > 0:
        return

    path = os.path.join(os.path.dirname(__file__), "../../../../sample_data/%s.json" % sample_name)
    with open(path) as fh:
        data = json.load(fh)

    MockAgentRpc.mock_servers = dict([[h['address'], h] for h in data['hosts']])
    load_string(json.dumps(data))

    from chroma_core.models.target import ManagedTarget
    # NB: This can take a while -- fixtures would be faster, but then we'd
    # need to maintain them.
    for target in ManagedTarget.objects.all():
        context.test_case.set_state(target.downcast(), "mounted")

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
    from tests.unit.chroma_core.helper import MockAgentRpc

    # Skip setup if it was already done in a previous scenario.
    if len(MockAgentRpc.mock_servers) > 0:
        return

    path = os.path.join(os.path.dirname(__file__), "../../../../sample_data/%s.json" % name)
    with open(path) as fh:
        data = json.load(fh)

    MockAgentRpc.mock_servers = dict([[h['address'], h] for h in data['hosts']])


@given('the mock servers are set up')
def step(context):
    from chroma_core.models.host import ManagedHost, VolumeNode
    from tests.unit.chroma_core.helper import MockAgentRpc

    for address, host_info in sorted(MockAgentRpc.mock_servers.items()):
        if not ManagedHost.objects.filter(fqdn = host_info['fqdn']).exists():
            ManagedHost.create(host_info['fqdn'], host_info['nodename'], ['manage_targets'], address = address)

    for address, host_info in sorted(MockAgentRpc.mock_servers.items()):
        if not VolumeNode.objects.filter(host__fqdn = host_info['fqdn'], path__startswith = "/fake/path/").exists():
            context.test_case._test_lun(ManagedHost.objects.get(fqdn = host_info['fqdn']))

    eq_(ManagedHost.objects.count(), len(MockAgentRpc.mock_servers))


@given('the config has been reset to defaults')
def step(context):
    from chroma_cli.config import Configuration
    from chroma_cli.defaults import defaults
    context.cli_config = Configuration()
    context.cli_config.update(defaults)
