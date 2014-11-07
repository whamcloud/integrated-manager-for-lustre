#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from collections import defaultdict, namedtuple
import os
import glob
import datetime
import ConfigParser

from chroma_agent.chroma_common.lib import shell
from chroma_agent.log import daemon_log
from chroma_agent.log import console_log
from chroma_agent.utils import Mounts
from chroma_agent import version as agent_version
from chroma_agent.plugin_manager import DevicePlugin, ActionPluginManager
from chroma_agent.device_plugins.linux import LinuxDevicePlugin
from chroma_agent.chroma_common.lib.exception_sandbox import exceptionSandBox
import chroma_agent.lib.normalize_device_path as ndp


from chroma_agent.chroma_common.filesystems.filesystem import FileSystem
from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice

# FIXME: weird naming, 'LocalAudit' is the class that fetches stats
from chroma_agent.device_plugins.audit.local import LocalAudit


VersionInfo = namedtuple('VersionInfo', ['epoch', 'version', 'release', 'arch'])

REPO_PATH = "/etc/yum.repos.d/Intel-Lustre-Agent.repo"


@exceptionSandBox(console_log, None)
def scan_packages():
    """
    Interrogate the packages available from configured repositories, and the installation
    status of those packages.
    """

    # Local import so that this module can be imported in pure python
    # environments as well as on Linux.
    import rpm

    # Look up what repos are configured
    # =================================
    if not os.path.exists(REPO_PATH):
        return None

    cp = ConfigParser.SafeConfigParser()
    cp.read(REPO_PATH)
    repo_names = cp.sections()
    repo_packages = dict([(name, defaultdict(lambda: {'available': [], 'installed': []})) for name in repo_names])

    # For all repos, enumerate packages in the repo
    # =============================================
    shell.try_run(["yum", "--disablerepo=*", "--enablerepo=%s" % ",".join(repo_names), "clean", "all"])
    for repo_name, packages in repo_packages.items():
        try:
            stdout = shell.try_run(["repoquery", "--repoid=%s" % repo_name, "-a", "--qf=%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{ARCH}"])

            # Returning nothing means the package was not found at all and so we have no data to deliver back.
            if stdout:
                for line in [l.strip() for l in stdout.strip().split("\n")]:
                    epoch, name, version, release, arch = line.split()
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
    ts = rpm.TransactionSet()
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


@exceptionSandBox(console_log, {})
class LustrePlugin(DevicePlugin):
    def _scan_mounts(self):
        mounts = {}

        for device, mntpnt, fstype in Mounts().all():
            if fstype != 'lustre':
                continue

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
                except shell.CommandExecutionError:
                    continue

            dev_normalized = ndp.normalized_device_path(device)

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
            if not k in mounts:
                del self._mount_cache[k]

        return mounts.values()

    def _scan(self, initial=False):
        started_at = datetime.datetime.utcnow().isoformat() + "Z"
        audit = LocalAudit()

        # Only set resource_locations if we have the management package
        try:
            from chroma_agent.action_plugins.manage_targets import get_resource_locations
            resource_locations = get_resource_locations()
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
            "capabilities": ActionPluginManager().capabilities,
            "metrics": audit.metrics(),
            "properties": audit.properties(),
            "mounts": mounts,
            "packages": packages,
            "resource_locations": resource_locations
        }

    def start_session(self):
        self._mount_cache = defaultdict(dict)

        return self._scan(initial=True)

    def update_session(self):
        return self._scan()
