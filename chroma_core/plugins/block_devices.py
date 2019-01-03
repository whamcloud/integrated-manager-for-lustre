# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import json
from logging import DEBUG

import settings
from chroma_core.services import log_register

log = log_register("plugin_runner")
log.setLevel(DEBUG)


def _fetch_aggregator():
    import requests

    resp = requests.get(settings.DEVICE_AGGREGATOR_URL)
    payload = resp.text

    return json.loads(payload)


def get_devices(fqdn):
    try:
        _data = _fetch_aggregator()
        return _data[fqdn]
    except Exception as e:
        log.error(
            "iml-device-aggregator is not providing expected data, ensure "
            "iml-device-scanner package is installed and relevant "
            "services are running on storage servers (%s)" % e
        )
        return {}
