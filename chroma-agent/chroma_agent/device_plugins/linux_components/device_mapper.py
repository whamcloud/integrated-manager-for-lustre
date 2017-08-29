# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import re
import errno

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log
import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.device_plugins.linux_components.block_devices import BlockDevices
from iml_common.blockdevices.blockdevice import BlockDevice
from iml_common.lib import util


class DmsetupTable(object):
    """Uses various devicemapper commands to learn about LVM and Multipath"""

    def __init__(self, block_devices):
        self.block_devices = block_devices
        self.mpaths = {}
        self.vgs = {}
        self.lvs = {}

        for vg_name, vg_uuid, vg_size in self._get_vgs():
            self.vgs[vg_name] = {
                'name': vg_name,
                'uuid': vg_uuid,
                'size': vg_size,
                'pvs_major_minor': []}
            self.lvs[vg_name] = {}
            for lv_name, lv_uuid, lv_size, lv_path in self._get_lvs(vg_name):
                # Do this to cache the device, type see blockdevice and filesystem for info.
                BlockDevice('lvm_volume', '/dev/mapper/%s-%s' % (vg_name, lv_name))

                self.lvs[vg_name][lv_name] = {
                    'name': lv_name,
                    'uuid': lv_uuid,
                    'size': lv_size}

        stdout = AgentShell.try_run(['dmsetup', 'table'])
        self._parse_dm_table(stdout)

    def _get_vgs(self):
        try:
            out = AgentShell.try_run(["vgs", "--units", "b", "--noheadings", "-o", "vg_name,vg_uuid,vg_size"])
        except OSError as os_error:
            # If no vgs installed then no volume groups
            if os_error.errno == errno.ENOENT:
                return
            raise

        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            name, uuid, size_str = line.split()
            size = util.human_to_bytes(size_str)
            yield (name, uuid, size)

    def _get_lvs(self, vg_name):
        try:
            out = AgentShell.try_run(["lvs", "--units", "b", "--noheadings", "-o", "lv_name,lv_uuid,lv_size,lv_path", vg_name])
        except OSError as os_error:
            # If no lvs install then no logical volumes
            if os_error.errno == errno.ENOENT:
                return
            raise

        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            name, uuid, size_str, path = line.split()
            size = util.human_to_bytes(size_str)
            yield (name, uuid, size, path)

    def _parse_multipath_params(self, tokens):
        """
        Parse a multipath line from 'dmsetup table', starting after 'multipath'
        """
        # We will modify this, take a copy
        tokens = list(tokens)

        # integer count arguments, followed by list of strings
        n_feature_args = int(tokens[0])
        #feature_args = tokens[1:1 + n_feature_args]
        tokens = tokens[n_feature_args + 1:]

        # integer count arguments, followed by list of strings
        n_handler_args = int(tokens[0])
        #handler_args = tokens[1:1 + n_handler_args]
        tokens = tokens[n_handler_args + 1:]

        #num_groups, init_group_number = int(tokens[0]), int(tokens[1])
        tokens = tokens[2:]

        devices = []

        while len(tokens):
            path_selector, status, path_count, path_arg_count = tokens[0:4]

            # Sanity check of parsing, is the path selector one of those in 2.6.x linux kernel
            assert path_selector in ['round-robin', 'queue-length', 'service-time']
            path_arg_count = int(path_arg_count)
            path_count = int(path_count)

            # status is a call to ps.type->status with path=NULL, which for all linux 2.6 path selectors is always "0"
            # path_count is the number of paths in this priority group
            # path_arg_count is the number of args that each path will have after the block device identifier (a constant
            # for each path_selector)

            tokens = tokens[4:]
            for i in range(0, path_count):
                major_minor = tokens[0]
                # path_status_args = tokens[1:1 + path_arg_count]
                # The meaning of path_status_args depends on path_selector:
                #  for round-robin, and queue-length it is repeat_count (1 integer)
                #  for service-time it is repeat_count then relative_throughput (2 integers)
                tokens = tokens[1 + path_arg_count:]
                devices.append(major_minor)

        return devices

    def _parse_dm_table(self, stdout):
        if stdout.strip() == "No devices found":
            dm_lines = []
        else:
            dm_lines = [i for i in stdout.split("\n") if len(i) > 0]

        # Compose a lookup of names of multipath devices, for use
        # in parsing other lines
        multipath_names = set()
        for line in dm_lines:
            tokens = line.split()
            name = tokens[0].strip(":")
            dm_type = tokens[3]
            if dm_type == 'multipath':
                multipath_names.add(name)

        def _read_lv(block_device, lv_name, vg_name, devices):
            self.lvs[vg_name][lv_name]['block_device'] = block_device

            devices = [self.block_devices.block_device_nodes[i]['major_minor'] for i in devices]
            self.vgs[vg_name]['pvs_major_minor'] = list(set(self.vgs[vg_name]['pvs_major_minor']) | set(devices))

        def _read_lv_partition(block_device, parent_lv_name, vg_name):
            # HYD-744: FIXME: compose path in a way that copes with hyphens
            parent_block_device = self.block_devices.node_block_devices["%s/%s-%s" % (BlockDevices.MAPPERPATH, vg_name, parent_lv_name)]
            self.block_devices.block_device_nodes[block_device]['parent'] = parent_block_device

        def _read_mpath_partition(block_device, parent_mpath_name):
            # A non-LV partition
            parent_block_device = self.block_devices.node_block_devices["%s/%s" % (BlockDevices.MAPPERPATH, parent_mpath_name)]
            self.block_devices.block_device_nodes[block_device]['parent'] = parent_block_device

        # Make a note of which VGs/LVs are in the table so that we can
        # filter out nonlocal LVM components.
        local_lvs = set()
        local_vgs = set()

        for line in dm_lines:
            tokens = line.split()
            name = tokens[0].strip(":")
            dm_type = tokens[3]

            node_path = os.path.join(BlockDevices.MAPPERPATH, name)
            block_device = self.block_devices.node_block_devices[node_path]

            if dm_type in ['linear', 'striped']:
                # This is either an LV or a partition.
                # Try to resolve its name to a known LV, if not found then it
                # is a partition.
                # This is an LVM LV
                if dm_type == 'striped':
                    # List of striped devices
                    dev_indices = range(6, len(tokens), 2)
                    devices = [tokens[i] for i in dev_indices]
                elif dm_type == 'linear':
                    # Single device linear range
                    devices = [tokens[4]]
                else:
                    console_log.error("Failed to parse dmsetupline '%s'" % line)
                    continue

                # To be an LV:
                #  Got to have a hyphen
                #  Got to appear in lvs dict

                # To be a partition:
                #  Got to have a (.*)p\d+$
                #  Part preceeding that pattern must be an LV or a mpath

                # Potentially confusing scenarios:
                #  A multipath device named foo-bar where there exists a VG called 'foo'
                #  An LV whose name ends "p1" like foo-lvp1
                #  NB some scenarios may be as confusing for devicemapper as they are for us, e.g.
                #  if someone creates an LV "bar" in a VG "foo", and also an mpath called "foo-bar"

                # First, let's see if it's an LV or an LV partition
                match = re.search("(.*[^-])-([^-].*)", name)
                if match:
                    vg_name, lv_name = match.groups()
                    # When a name has a "-" in it, DM prints a double hyphen in the output
                    # So for an LV called "my-lv" you get VolGroup00-my--lv
                    vg_name = vg_name.replace("--", "-")
                    lv_name = lv_name.replace("--", "-")
                    try:
                        vg_lv_info = self.lvs[vg_name]
                        local_vgs.add(vg_name)
                    except KeyError:
                        # Part before the hyphen is not a VG, so this can't be an LV
                        pass
                    else:
                        if lv_name in vg_lv_info:
                            _read_lv(block_device, lv_name, vg_name, devices)
                            local_lvs.add(lv_name)
                            continue
                        else:
                            # It's not an LV, but it matched a VG, could it be an LV partition?
                            result = re.search("(.*)p\d+", lv_name)
                            if result:
                                lv_name = result.groups()[0]
                                if lv_name in vg_lv_info:
                                    # This could be an LV partition.
                                    _read_lv_partition(block_device, lv_name, vg_name)
                                    local_lvs.add(lv_name)
                                    continue
                else:
                    # If it isn't an LV or an LV partition, see if it looks like an mpath partition
                    result = re.search("(.*)p\d+", name)
                    if result:
                        mpath_name = result.groups()[0]
                        if mpath_name in multipath_names:
                            _read_mpath_partition(block_device, mpath_name)
                        else:
                            # Part before p\d+ is not an mpath, therefore not a multipath partition
                            pass
                    else:
                        # No trailing p\d+, therefore not a partition
                        console_log.error("Cannot handle devicemapper device %s: it doesn't look like an LV or a partition" % name)
            elif dm_type == 'multipath':
                if name in self.mpaths:
                    raise RuntimeError("Duplicated mpath device %s" % name)

                major_minors = self._parse_multipath_params(tokens[4:])

                # multipath devices might reference devices that don't exist (maybe did and the removed) so
                # becareful about missing keys.
                devices = [self.block_devices.block_device_nodes[major_minor]
                           for major_minor in major_minors
                           if major_minor in self.block_devices.block_device_nodes]

                # Add this devices to the canonical path list.
                for device in devices:
                    ndp.add_normalized_device(device['path'], "%s/%s" % (BlockDevices.MAPPERPATH, name))

                self.mpaths[name] = {"name": name,
                                     "block_device": block_device,
                                     "nodes": devices}
            else:
                continue

        # Filter out nonlocal LVM components (HYD-2431)
        self.vgs = dict([(vg, value) for vg, value in self.vgs.items() if vg in local_vgs])
        self.lvs = dict([(lv, value) for lv, value in self.lvs.items() if lv in local_vgs])
        for vg_name, vg_lvs in self.lvs.items():
            self.lvs[vg_name] = dict([(k, v) for k, v in self.lvs[vg_name].items() if k in local_lvs])
