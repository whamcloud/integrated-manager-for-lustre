# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import time
from logging import DEBUG

import settings
from chroma_core.services import log_register

log = log_register("plugin_runner")
log.setLevel(DEBUG)


def _fetch_aggregator(timeout):
    import requests

    summary = 0.0
    timeout = timeout if timeout >= 0 else 0
    while summary <= timeout:
        resp = requests.get(settings.DEVICE_AGGREGATOR_PROXY_PASS)
        summary += resp.elapsed.seconds
        summary += resp.elapsed.microseconds / 10.0 ** 6

        try:
            return resp.json(), summary
        except ValueError as e:
            # This error might be casused by device-aggregator not being ready
            # yet or communication breakdown inside EMF server side
            log.error(
                "emf-device-aggregator is not providing expected data, ensure "
                "this is not caused by race condition (%s)" % e
            )
            # So it is better to wait for service startup
            if summary < timeout:
                time.sleep(0.1)
                summary += 0.1
    return {}, summary


def get_devices(fqdn, timeout=0):
    summary = 0.0
    timeout = timeout if timeout >= 0 else 0

    while summary <= timeout:
        try:
            _data, elapsed = _fetch_aggregator(timeout - summary)
            summary += elapsed
            return _data[fqdn]
        except (KeyError, TypeError) as e:
            # This error might be caused by fact that device-aggregator
            # hasn't yet received device information update on startup
            log.error(
                "emf-device-aggregator is not providing expected data for fqdn {}. Waited: {},"
                "Trying again for: {}, Error: {}".format(fqdn, summary, timeout - summary, e)
            )
            # So it is better to wait for it if possible
            if summary < timeout:
                time.sleep(0.1)
                summary += 0.1
    return {}
