# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict, namedtuple
import os
import glob
import ConfigParser

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log
from chroma_agent.log import console_log
from chroma_agent import version as agent_version
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent import plugin_manager
from chroma_agent.device_plugins.linux import LinuxDevicePlugin
from iml_common.lib.exception_sandbox import exceptionSandBox
from chroma_agent.device_plugins.block_devices import get_normalized_device_table, get_local_mounts
from chroma_agent.lib.yum_utils import yum_util
from iml_common.lib.date_time import IMLDateTime

from iml_common.filesystems.filesystem import FileSystem
from iml_common.blockdevices.blockdevice import BlockDevice

# FIXME: weird naming, 'LocalAudit' is the class that fetches stats
from chroma_agent.device_plugins.audit import local


VersionInfo = namedtuple('VersionInfo', ['epoch', 'version', 'release', 'arch'])

REPO_PATH = "/etc/yum.repos.d/Intel-Lustre-Agent.repo"

# import so that this module can be imported in pure python environments as well as on Linux.
# Doing it this way means that rpm_lib can mocked.
try:
    import rpm as rpm_lib
except:
    rpm_lib = None


@exceptionSandBox(console_log, None)
def scan_packages():
    """
    Interrogate the packages available from configured repositories, and the installation
    status of those packages.
    """

    # Look up what repos are configured
    # =================================
    if not os.path.exists(REPO_PATH):
        return None

    cp = ConfigParser.SafeConfigParser()
    cp.read(REPO_PATH)
    repo_names = sorted(cp.sections())
    repo_packages = dict([(name, defaultdict(lambda: {'available': [], 'installed': []})) for name in repo_names])

    # For all repos, enumerate packages in the repo in alphabetic order
    # =================================================================
    yum_util('clean', fromrepo=repo_names)

    # For all repos, query packages in alphabetical order
    # ===================================================
    for repo_name in repo_names:
        packages = repo_packages[repo_name]
        try:
            stdout = yum_util('repoquery', fromrepo=[repo_name])

            # Returning nothing means the package was not found at all and so we have no data to deliver back.
            if stdout:
                for line in [l.strip() for l in stdout.strip().split("\n")]:
                    if line.startswith("Last metadata expiration check") or \
                       line.startswith("Waiting for process with pid"):
                        continue
                    epoch, name, version, release, arch = line.split()
                    if arch == "src":
                        continue
                    packages[name]['available'].append(VersionInfo(
                        epoch=epoch,
                        version=version,
                        release=release,
                        arch=arch))
        except ValueError, e:
            console_log.error("bug HYD-2948. repoquery Output: %s" % (stdout))
            raise e
        except RuntimeError, e:
            # This is a network operation, so cope with it failing
            daemon_log.error(e)
            return None

    # For all packages named in the repos, get installed version if it is installed
    # =============================================================================
    ts = rpm_lib.TransactionSet()
    for repo_name, packages in repo_packages.items():
        for package_name, package_data in packages.items():
            headers = ts.dbMatch('name', package_name)
            for h in headers:
                package_data['installed'].append(VersionInfo(
                    epoch=h['epochnum'].__str__(),
                    version=h['version'],
                    release=h['release'],
                    arch=h['arch']
                ))

    return repo_packages


def process_zfs_mount(device, data, zfs_mounts):
    # If zfs-backed target/dataset, lookup underlying pool to get uuid
    # and nested dataset in zed structures to access lustre svname (label).
    dev_root = device.split('/')[0]
    if dev_root not in [d for d, m, f in zfs_mounts]:
        return None, None, None

    pool = next(
        p for p in data['zed'].values()
        if p['name'] == dev_root
    )
    dataset = next(
        d for d in pool['datasets']
        if d['name'] == device
    )

    fs_label = next(
        p['value'] for p in dataset['props']
        if p['name'] == 'lustre:svname'  # used to be fsname
    )

    fs_uuid = dataset['guid']

    # note: this will be one of the many partitions that belong to the pool
    new_device = next(
        child['Disk']['path'] for child in pool['vdev']['Root']['children']
        if child.get('Disk')
    )

    return fs_label, fs_uuid, new_device


class LustrePlugin(DevicePlugin):
    delta_fields = ['capabilities', 'properties', 'mounts', 'packages', 'resource_locations']

    def __init__(self, session):
        self.reset_state()
        super(LustrePlugin, self).__init__(session)

    def reset_state(self):
        self._mount_cache = defaultdict(dict)

    @exceptionSandBox(console_log, {})
    def _scan_mounts(self):
        mounts = {}

        local_mounts = get_local_mounts()
        zfs_mounts = [(d, m, f) for d, m, f in local_mounts if f == 'zfs']

        for device, mntpnt, fstype in local_mounts:
            if fstype != 'lustre':
                continue

            fs_label, fs_uuid, new_device = process_zfs_mount(device, data, zfs_mounts)

            if not fs_label:
                # todo: derive information directly from device-scanner output
                # Assume that while a filesystem is mounted, its UUID and LABEL don't change.
                # Therefore we can avoid repeated blkid calls with a little caching.
                if device in self._mount_cache:
                    fs_uuid = self._mount_cache[device]['fs_uuid']
                    fs_label = self._mount_cache[device]['fs_label']
                else:
                    # Sending none as the type means BlockDevice will use it's local cache to work the type.
                    # This is not a good method, and we should work on a way of not storing such state but for the
                    # present it is the best we have.
                    try:
                        fs_uuid = BlockDevice(None, device).uuid
                        fs_label = FileSystem(None, device).label

                        # If we have scanned the devices then it is safe to cache the values.
                        if LinuxDevicePlugin.devices_scanned:
                            self._mount_cache[device]['fs_uuid'] = fs_uuid
                            self._mount_cache[device]['fs_label'] = fs_label
                    except AgentShell.CommandExecutionError:
                        continue

            ndt = get_normalized_device_table()
            dev_normalized = ndt.normalized_device_path(device if not new_device else new_device)

            recovery_status = {}
            try:
                recovery_file = glob.glob("/proc/fs/lustre/*/%s/recovery_status" % fs_label)[0]
                recovery_status_text = open(recovery_file).read()
                for line in recovery_status_text.split("\n"):
                    tokens = line.split(":")
                    if len(tokens) != 2:
                        continue
                    k = tokens[0].strip()
                    v = tokens[1].strip()
                    recovery_status[k] = v
            except IndexError:
                # If the recovery_status file doesn't exist,
                # we will return an empty dict for recovery info
                pass

            mounts[device] = {
                'device': dev_normalized,
                'fs_uuid': fs_uuid,
                'mount_point': mntpnt,
                'recovery_status': recovery_status
            }

        # Drop cached info about anything that is no longer mounted
        for k in self._mount_cache.keys():
            if k not in mounts:
                del self._mount_cache[k]

        return mounts.values()

    def _scan(self, initial=False):
        started_at = IMLDateTime.utcnow().isoformat()
        audit = local.LocalAudit()

        # Only set resource_locations if we have the management package
        try:
            from chroma_agent.action_plugins import manage_targets
            resource_locations = manage_targets.get_resource_locations()
        except ImportError:
            resource_locations = None

        mounts = self._scan_mounts()

        if initial:
            packages = scan_packages()
        else:
            packages = None

        # FIXME: HYD-1095 we should be sending a delta instead of a full dump every time
        # FIXME: At this time the 'capabilities' attribute is unused on the manager
        return {
            "started_at": started_at,
            "agent_version": agent_version(),
            "capabilities": plugin_manager.ActionPluginManager().capabilities,
            "metrics": audit.metrics(),
            "properties": audit.properties(),
            "mounts": mounts,
            "packages": packages,
            "resource_locations": resource_locations
        }

    def start_session(self):
        self.reset_state()
        self._reset_delta()
        return self._delta_result(self._scan(initial=True), self.delta_fields)

    def update_session(self):
        return self._delta_result(self._scan(), self.delta_fields)
