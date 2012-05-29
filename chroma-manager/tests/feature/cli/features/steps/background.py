#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from nose.tools import *
from behave import *


@given('the "{sample_name}" data is loaded')
def step(context, sample_name):
    import os
    import simplejson as json
    import chroma_core.lib.agent

    from chroma_core.models.filesystem import ManagedFilesystem
    # Don't reload all of this if a previous scenario set it up
    # and it hasn't been torn down again.
    if ManagedFilesystem.objects.count() > 0:
        return

    path = os.path.join(os.path.dirname(__file__), "../../../../sample_data/%s.json" % sample_name)
    with open(path) as fh:
        data = json.load(fh)

    chroma_core.lib.agent.Agent.mock_servers = dict([[h['address'], h] for h in data['hosts']])
    from chroma_core.lib.load_config import load_string
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
    ok_(ManagedHost.objects.count() == len(chroma_core.lib.agent.Agent.mock_servers.keys()))
