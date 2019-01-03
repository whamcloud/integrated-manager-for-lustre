# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from argparse import REMAINDER, SUPPRESS
import sys
import traceback

from chroma_cli.parser import ResettableArgumentParser
from chroma_cli.config import Configuration
from chroma_cli.api import ApiHandle
from chroma_cli.output import StandardFormatter
from chroma_cli.handlers import Dispatcher
from chroma_cli.exceptions import ApiException, AbnormalCommandCompletion, UserConfirmationRequired


def detect_proxies():
    from chroma_cli.defaults import PROXY_VARIABLES
    import os

    proxies = []
    for proxy in PROXY_VARIABLES:
        if proxy in os.environ:
            proxies.append(proxy)
    return proxies


def standard_cli(args=None, config=None):
    config = config
    if not config:
        config = Configuration()
    parser = ResettableArgumentParser(description="Chroma CLI", add_help=False)
    dispatcher = Dispatcher()

    parser.add_argument("--api_url", help="Entry URL for Chroma API")
    parser.add_argument("--username", help="Chroma username")
    parser.add_argument("--password", help="Chroma password")
    parser.add_argument("--output", "-o", help="Output format", choices=StandardFormatter.formats())
    parser.add_argument("--nowait", "-n", help="Don't wait for jobs to complete", action="store_true")
    parser.add_argument("--noproxy", "-x", help="Ignore $HTTP_PROXY, if present", action="store_true")
    parser.add_argument("--force", "-f", help="Ignore validation errors and proceed anyway", action="store_true")
    parser.clear_resets()

    # fake-y help arg to allow it to pass through to the real one
    parser.add_argument("--help", "-h", help="show this help message and exit", default=SUPPRESS, action="store_true")
    parser.add_argument("args", nargs=REMAINDER)
    ns = parser.parse_args(args)
    parser.reset()

    parser.add_argument("--help", "-h", help="show this help message and exit", default=SUPPRESS, action="help")
    subparsers = parser.add_subparsers()
    dispatcher.add_subparsers(subparsers, ns)

    if "noun" in ns and "verb" in ns:
        args = [ns.noun, ns.verb] + ns.args
    ns = parser.parse_args(args, ns)

    # Allow CLI options to override defaults/.chroma config values
    config.update(
        dict([[key, val] for key, val in ns.__dict__.items() if val and key not in ["primary_action", "options"]])
    )

    authentication = {"username": config.username, "password": config.password}
    api = ApiHandle(api_uri=config.api_url, authentication=authentication)

    formatter = StandardFormatter(format=config.output, nowait=config.nowait, command_monitor=api.command_monitor)

    proxies = detect_proxies()
    if proxies and config.noproxy:
        import os

        for proxy in proxies:
            del os.environ[proxy]
    elif proxies:
        sys.stderr.write(
            "WARNING: Detected the following proxy variables: %s (--noproxy to disable them)\n" % ", ".join(proxies)
        )

    try:
        ns.handler(api=api, formatter=formatter)(parser=parser, args=args, ns=ns)
    except UserConfirmationRequired as e:
        print(e)
        response = ""
        while response not in ["yes", "no"]:
            response = raw_input("Do you want to proceed (--%s to avoid prompt)? (yes/no) " % e.skip_argument).lower()

        if response == "yes":
            setattr(ns, e.skip_argument, True)
            ns.handler(api=api, formatter=formatter)(parser=parser, args=args, ns=ns)
    except (AbnormalCommandCompletion, ApiException) as e:
        print(e)
        sys.exit(1)
    except Exception as e:
        exc_info = sys.exc_info()
        trace = "\n".join(traceback.format_exception(*(exc_info or sys.exc_info())))
        handler = "unknown"
        if "handler" in ns:
            handler = ns.handler.nouns[0]
            if "verb" in ns:
                handler += ".%s" % ns.verb
        print("Internal client error from handler '%s': %s" % (handler, trace))
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    standard_cli()
