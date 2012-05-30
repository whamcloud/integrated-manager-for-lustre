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

    ok_(entity_map[entity].objects.count() == int(count))
