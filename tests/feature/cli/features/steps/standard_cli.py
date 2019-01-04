#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

import os
from behave import *
from nose.tools import *

from chroma_cli.main import standard_cli
from helpers import fail


@when("I run chroma {args}")
def step(context, args):
    from StringIO import StringIO
    import sys

    context.stdin = StringIO()
    context.stdout = StringIO()
    context.stderr = StringIO()

    try:
        sys.stdin = context.stdin
        sys.stdout = context.stdout
        sys.stderr = context.stderr

        if [s for s in context.scenario.steps if "should be prompted" in s.name]:
            # Fake this out for scenarios that expect a prompt
            sys.stdin.write("yes\n")
        else:
            # Scenarios that don't expect a prompt but get one will fail
            sys.stdin.write("no\n")
        sys.stdin.seek(0)

        if "cli_config" in context and context.cli_config:
            standard_cli(args=args.split(), config=context.cli_config)
        else:
            # Set env vars for username/password so that we don't need
            # to pollute the features files with them.
            os.environ["CHROMA_USERNAME"] = "admin"
            os.environ["CHROMA_PASSWORD"] = "lustre"
            standard_cli(args.split())

    except SystemExit as e:
        context.stdout.seek(0)
        context.stderr.seek(0)
        forced = any([a in ["--force", "-f"] for a in args.split()])
        if e.code != 0 and not context.cli_failure_expected:
            fail("code: %d stdout: %s stderr: %s" % (e.code, context.stdout.readlines(), context.stderr.readlines()))
        elif e.code == 0 and context.cli_failure_expected and not forced:
            fail(
                "Failure expected but didn't happen!\nstdout: %s, stderr: %s"
                % (context.stdout.readlines(), context.stderr.readlines())
            )
    except Exception as e:
        context.stdout.seek(0)
        context.stderr.seek(0)
        from traceback import format_exc

        fail(
            "%s\nstdout:\n%s\nstderr:\n%s"
            % (format_exc(), "".join(context.stdout.readlines()), "".join(context.stderr.readlines()))
        )

    sys.stdin = sys.__stdin__
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__


@given("The following commands will fail")
def step(context):
    context.cli_failure_expected = True


@then('I should see output containing "{message}"')
def step(context, message):
    context.stdout.seek(0)
    stdout = context.stdout.read()
    assert message in stdout, stdout


@then("I should be prompted to proceed")
def step(context):
    context.stdout.seek(0)
    stdout = context.stdout.read()
    assert "Do you want to proceed" in stdout, stdout


@then('I should not see output containing "{message}"')
def step(context, message):
    context.stdout.seek(0)
    try:
        ok_(message not in "".join(context.stdout.readlines()))
    except AssertionError:
        context.stdout.seek(0)
        print(context.stdout.readlines())
        raise
