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
    from tests.unit.chroma_core.helper import MockAgent

    from chroma_core.models.filesystem import ManagedFilesystem
    # Don't reload all of this if a previous scenario set it up
    # and it hasn't been torn down again.
    if ManagedFilesystem.objects.count() > 0:
        return

    path = os.path.join(os.path.dirname(__file__), "../../../../sample_data/%s.json" % sample_name)
    with open(path) as fh:
        data = json.load(fh)

    MockAgent.mock_servers = dict([[h['address'], h] for h in data['hosts']])
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
    eq_(ManagedHost.objects.count(), len(MockAgent.mock_servers.keys()))


@given('the "{name}" mocks are loaded')
def step(context, name):
    import os
    import json
    from tests.unit.chroma_core.helper import MockAgent

    # Skip setup if it was already done in a previous scenario.
    if len(MockAgent.mock_servers) > 0:
        return

    path = os.path.join(os.path.dirname(__file__), "../../../../sample_data/%s.json" % name)
    with open(path) as fh:
        data = json.load(fh)

    MockAgent.mock_servers = dict([[h['address'], h] for h in data['hosts']])


@given('the mock servers are set up')
def step(context):
    from chroma_core.models.host import ManagedHost
    from tests.unit.chroma_core.helper import MockAgent

    # Skip setup if it was already done in a previous scenario.
    if ManagedHost.objects.count() > 0:
        return

    for address, host_info in sorted(MockAgent.mock_servers.items()):
        host = ManagedHost.create(host_info['fqdn'], host_info['nodename'], ['manage_targets'], address = address)[0]
        context.test_case._test_lun(host)

    eq_(ManagedHost.objects.count(), len(MockAgent.mock_servers))


@given('the config has been reset to defaults')
def step(context):
    from chroma_cli.config import Configuration
    from chroma_cli.defaults import defaults
    context.cli_config = Configuration()
    context.cli_config.update(defaults)
