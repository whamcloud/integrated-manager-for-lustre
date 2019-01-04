from nose.tools import *
from behave import *


def fail(msg=None):
    raise AssertionError(msg)


@given("the {entity} count should be {count}")
@then("the {entity} count should be {count}")
def step(context, entity, count):
    from chroma_core.models import ManagedHost, ManagedFilesystem, ManagedTarget, ManagedOst, ManagedMgs, ManagedMdt

    entity_map = {
        "server": ManagedHost,
        "filesystem": ManagedFilesystem,
        "target": ManagedTarget,
        "mgt": ManagedMgs,
        "mdt": ManagedMdt,
        "ost": ManagedOst,
    }

    eq_(entity_map[entity].objects.count(), int(count))


@given("there should be {count} lines of output")
@then("there should be {count} lines of output")
def step(context, count):
    context.stdout.seek(0)
    # NB: We're hard-coding -1 lines for the header -- this may not
    # be robust enough for the future.
    output_line_count = len(context.stdout.readlines()) - 1
    eq_(output_line_count, int(count))


@given("the {entity} {field} on {subject} should be {value}")
@then("the {entity} {field} on {subject} should be {value}")
def step(context, entity, field, subject, value):
    entity_map = {"server": "host"}

    from chroma_cli.api import ApiHandle

    ah = ApiHandle()
    try:
        endpoint = entity_map[entity]
    except KeyError:
        endpoint = entity
    resource = ah.endpoints[endpoint].show(subject)

    import re

    match = re.match("^the same as (\w+)$", value)
    if match:
        value = resource.all_attributes[match.group(1)]

    eq_(resource.all_attributes[field], value)


@given("the config parameter {key} should be set to {value}")
@then("the config parameter {key} should be set to {value}")
def step(context, key, value):
    from chroma_cli.defaults import defaults

    if value == "the default":
        eq_(getattr(context.cli_config, key), defaults[key])
    elif value == "True":
        eq_(getattr(context.cli_config, key), True)
    else:
        eq_(getattr(context.cli_config, key), value)


@given("the {testkey} host contact test should {result}")
@then("the {testkey} host contact test should {result}")
def step(context, testkey, result):
    value = {"fail": False, "succeed": True}[result]
    kwargs = {testkey: value}
    # This business of reaching into context._runner.hooks is necessitated
    # by the lack of a good place to put these things.  Sigh.
    context._runner.hooks["patch_test_host_contact_task"](context, kwargs)
    context.cli_failure_expected = not value


@given("the boot_time on {hostname} has been recorded")
def step(context, hostname):
    from chroma_cli.api import ApiHandle

    ah = ApiHandle()
    resource = ah.endpoints["host"].show(hostname)

    context.server_boot_time = resource.all_attributes["boot_time"]


@then("the boot_time on {hostname} should reflect a reboot")
def step(context, hostname):
    from chroma_cli.api import ApiHandle

    ah = ApiHandle()
    resource = ah.endpoints["host"].show(hostname)

    context.test_case.assertGreater(resource.all_attributes["boot_time"], context.server_boot_time)
