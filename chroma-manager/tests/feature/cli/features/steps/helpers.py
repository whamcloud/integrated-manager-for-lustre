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
    from chroma_core.models import ManagedHost
    entity_map = {'server': ManagedHost}

    eq_(entity_map[entity].objects.count(), int(count))


@given('the {entity} {field} on {subject} should be {value}')
@then('the {entity} {field} on {subject} should be {value}')
def step(context, entity, field, subject, value):
    entity_map = {'server': "host"}
    from chroma_cli.api import ApiHandle
    ah = ApiHandle()
    resource = ah.endpoints[entity_map[entity]].show(subject)

    eq_(resource.all_attributes[field], value)
