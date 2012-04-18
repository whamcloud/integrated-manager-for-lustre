#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.plugins import DevicePlugin


class FakeControllerDevicePlugin(DevicePlugin):
    def _read_config(self):
        import simplejson as json
        return json.loads(open("/root/fake_controller.json").read())

    def start_session(self):
        return self._read_config()

    def update_session(self):
        return self._read_config()
