from chroma_agent.plugin_manager import DevicePlugin


class FakeControllerDevicePlugin(DevicePlugin):
    def _read_config(self):
        import json
        return json.loads(open("/root/fake_controller.json").read())

    def start_session(self):
        return self._read_config()

    def update_session(self):
        return self._read_config()
