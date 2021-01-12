# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_agent.plugin_manager import DevicePlugin


class LinuxDevicePlugin(DevicePlugin):
    # Some places require that the devices have been scanned before then can operate correctly, this is because the
    # scan creates and stores some information that is use in other places. This is non-optimal because it gives the
    # agent some state which we try and avoid. But this flag does at least allow us to keep it neat.
    devices_scanned = False

    def __init__(self, session):
        super(LinuxDevicePlugin, self).__init__(session)

    def start_session(self):
        return {}

    def update_session(self):
        return {}
