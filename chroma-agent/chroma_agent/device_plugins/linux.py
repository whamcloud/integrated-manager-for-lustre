# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_agent.lib.shell import AgentShell
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent import config
from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices
from chroma_agent.device_plugins.linux_components.zfs import ZfsDevices
from chroma_agent.device_plugins.linux_components.device_mapper import DmsetupTable
from chroma_agent.device_plugins.linux_components.emcpower import EMCPower
from chroma_agent.device_plugins.linux_components.local_filesystems import LocalFilesystems
from chroma_agent.device_plugins.linux_components.mdraid import MdRaid


class LinuxDevicePlugin(DevicePlugin):
    # Some places require that the devices have been scanned before then can operate correctly, this is because the
    # scan creates and stores some information that is use in other places. This is non-optimal because it gives the
    # agent some state which we try and avoid. But this flag does at least allow us to keep it neat.
    devices_scanned = False

    def __init__(self, session):
        super(LinuxDevicePlugin, self).__init__(session)
        self._last_quick_scan_result = ""
        self._last_full_scan_result = None

    def _quick_scan(self):
        """Lightweight enumeration of available block devices"""
        return ZfsDevices().quick_scan() + BlockDevices.quick_scan()

    def _full_scan(self):
        # If we are a worker node then return nothing because our devices are not of interest. This is a short term
        # solution for HYD-3140. This plugin should really be loaded if it is not needed but for now this sorts out
        # and issue with PluginAgentResources being in the linux plugin.
        if config.get('settings', 'profile')['worker']:
            return {}

        # Before we do anything do a partprobe, this will ensure that everything gets an up to date view of the
        # device partitions. partprobe might throw errors so ignore return value
        AgentShell.run(["partprobe"])

        # Map of block devices major:minors to /dev/ path.
        block_devices = BlockDevices()

        # Devicemapper: LVM and Multipath
        dmsetup = DmsetupTable(block_devices)

        # Software RAID
        mds = MdRaid(block_devices).all()

        # _zpools
        zfs_devices = ZfsDevices()
        zfs_devices.full_scan(block_devices)

        # EMCPower Devices
        emcpowers = EMCPower(block_devices).all()

        # Local filesystems (not lustre) in /etc/fstab or /proc/mounts
        local_fs = LocalFilesystems(block_devices).all()

        # We have scan devices, so set the devices scanned flags.
        LinuxDevicePlugin.devices_scanned = True

        return {"vgs": dmsetup.vgs,
                "lvs": dmsetup.lvs,
                "zfspools": zfs_devices.zpools,
                "zfsdatasets": zfs_devices.datasets,
                "zfsvols": zfs_devices.zvols,
                "mpath": dmsetup.mpaths,
                "devs": block_devices.block_device_nodes,
                "local_fs": local_fs,
                'emcpower': emcpowers,
                'mds': mds}

    def _scan_devices(self, scan_always):
        full_scan_result = None

        if scan_always or (self._quick_scan() != self._last_quick_scan_result):
            self._last_quick_scan_result = self._quick_scan()
            full_scan_result = self._full_scan()
            self._last_full_scan_result = full_scan_result
        elif self._safety_send < DevicePlugin.FAILSAFEDUPDATE:
            self._safety_send += 1
        else:
            # The purpose of this is to cause the ResourceManager to re-evaluate the device-graph for this
            # host which may lead to different results if the devices reported from other hosts has changed
            # This should not really be required but is a harmless work around while we get the manager code
            # in order
            full_scan_result = self._last_full_scan_result

        if full_scan_result is not None:
            self._safety_send = 0

        return full_scan_result

    def start_session(self):
        return self._scan_devices(True)

    def update_session(self):
        trigger_plugin_update = self.trigger_plugin_update
        self.trigger_plugin_update = False
        scan_result = self._scan_devices(trigger_plugin_update)

        return scan_result
