#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

from nose.tools import *
from behave import *


def fail(msg=None):
    raise AssertionError(msg)


@given('the {entity} count should be {count}')
@then('the {entity} count should be {count}')
def step(context, entity, count):
    from chroma_core.models import ManagedHost, ManagedFilesystem, ManagedTarget, ManagedOst, ManagedMgs, ManagedMdt
    entity_map = {'server': ManagedHost,
                  'filesystem': ManagedFilesystem,
                  'target': ManagedTarget,
                  'mgt': ManagedMgs,
                  'mdt': ManagedMdt,
                  'ost': ManagedOst}

    eq_(entity_map[entity].objects.count(), int(count))


@given('the {entity} {field} on {subject} should be {value}')
@then('the {entity} {field} on {subject} should be {value}')
def step(context, entity, field, subject, value):
    entity_map = {'server': "host"}
    from chroma_cli.api import ApiHandle
    ah = ApiHandle()
    try:
        endpoint = entity_map[entity]
    except KeyError:
        endpoint = entity
    resource = ah.endpoints[endpoint].show(subject)

    import re
    match = re.match('^the same as (\w+)$', value)
    if match:
        value = resource.all_attributes[match.group(1)]

    eq_(resource.all_attributes[field], value)


@given('the config parameter {key} should be set to {value}')
@then('the config parameter {key} should be set to {value}')
def step(context, key, value):
    from chroma_cli.defaults import defaults
    if value == "the default":
        eq_(getattr(context.cli_config, key), defaults[key])
    elif value == "True":
        eq_(getattr(context.cli_config, key), True)
    else:
        eq_(getattr(context.cli_config, key), value)
