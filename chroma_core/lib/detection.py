# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.db import transaction
from chroma_core.lib.util import normalize_nid
from chroma_core.services import log_register
from chroma_core.models import NoNidsPresent
from chroma_core.models.devices import DeviceHost
from chroma_core.models.event import LearnEvent
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.models.host import ManagedHost, VolumeNode
from chroma_core.models.target import (
    ManagedMgs,
    ManagedTargetMount,
    ManagedTarget,
    FilesystemMember,
    ManagedMdt,
    ManagedOst,
)
from chroma_core.models.ticket import FilesystemTicket, MasterTicket
from chroma_core.lib.cache import ObjectCache
from chroma_help.help import help_text
import re


log = log_register(__name__)


class DetectScan(object):
    def __init__(self, step):
        self.created_filesystems = []
        self.discovered_filesystems = set()
        self.created_mgss = []
        self.created_targets = []
        self.step = step

    def log(self, message):
        self.step.log(message)

    def run(self, all_hosts_data):
        """:param all_hosts_data: Dict of ManagedHost to detect-scan output"""

        logs = []

        with transaction.atomic():
            self.all_hosts_data = all_hosts_data

            # Create ManagedMgs objects
            log.debug(">>learn_mgs_targets")
            self.learn_mgs_targets()

            # Create ManagedTargetMount objects
            log.debug(">>learn_mgs_target_mounts")
            self.learn_target_mounts()

            # Create ManagedMdt and ManagedOst objects
            log.debug(">>learn_fs_targets")
            self.learn_fs_targets()

            # Create ManagedTargetMount objects
            log.debug(">>learn_target_mounts")
            self.learn_target_mounts()

            # Assign a valid primary mount point,
            # and remove any targets which don't have a primary mount point
            for target in self.created_mgss + self.created_targets:
                if self.learn_primary_target(target):
                    for tm in target.managedtargetmount_set.all():
                        self._learn_event(tm.host, target)
                else:
                    logs.append(help_text["found_no_primary_mount_point_for_target"] % (target.target_type(), target))
                    target.mark_deleted()

            if not self.created_filesystems:
                logs.append(help_text["discovered_no_new_filesystem"])
            else:
                # Remove any Filesystems with zero MDTs or zero OSTs, or set state
                # of a valid filesystem
                for fs in self.created_filesystems:
                    mdts = ManagedMdt.objects.filter(filesystem=fs)
                    osts = ManagedOst.objects.filter(filesystem=fs)
                    if not mdts.count():
                        logs.append(help_text["found_not_TYPE_for_filesystem"] % ("MDT", fs.name))
                        fs.mark_deleted()
                    elif not osts.count():
                        logs.append(help_text["found_not_TYPE_for_filesystem"] % ("OST", fs.name))
                        fs.mark_deleted()
                    else:
                        logs.append(
                            help_text["discovered_filesystem_with_n_MDTs_and_n_OSTs"]
                            % (fs.name, mdts.count(), osts.count())
                        )

                        targets = fs.get_targets()

                        if all(t.state == "mounted" for t in targets):
                            fs.state = "available"

                        if not any(t.immutable_state for t in targets):
                            fs.immutable_state = False
                            fs.mdt_next_index = max(t.index for t in mdts) + 1
                            fs.ost_next_index = max(t.index for t in osts) + 1
                        fs.save()

                        first_target = fs.get_filesystem_targets()[0]
                        self._learn_event(first_target.primary_host, first_target)

                        # check for fs ticket
                        if self._has_ticket(first_target.primary_host, fs.name):
                            ticket = FilesystemTicket(state="granted", name=fs.name, filesystem=fs, ha_label=fs.name)
                            ticket.save()
                            logs.append(
                                help_text["discovered_target"]
                                % ("Filesystem Ticket", fs.name, first_target.primary_host)
                            )

            if not self.created_mgss:
                logs.append(help_text["discovered_no_new_target"] % ManagedMgs().target_type().upper())
            else:
                for mgt in self.created_mgss:
                    logs.append(
                        help_text["discovered_target"] % (mgt.target_type().upper(), mgt.name, mgt.primary_host)
                    )
                    # check for Master Ticket on discovered MGT
                    if self._has_ticket(mgt.primary_host, "lustre"):
                        ticket = MasterTicket(state="granted", name="lustre", mgs=mgt, ha_label="lustre")
                        ticket.save()
                        logs.append(help_text["discovered_target"] % ("Master Ticket", "lustre", mgt.primary_host))

            # Bit of additional complication so we can print really cracking messages, and detailed messages.
            for target in [ManagedMdt(), ManagedOst()]:
                if target.target_type() not in [target.target_type() for target in self.created_targets]:
                    logs.append(help_text["discovered_no_new_target"] % target.target_type().upper())

            for target in self.created_targets:
                logs.append(
                    help_text["discovered_target"] % (target.target_type().upper(), target.name, target.primary_host)
                )

        map(self.log, logs)

    def _has_ticket(self, host, ticket):
        if not ticket in self.all_hosts_data[host]["ha_list"]:
            return False
        ha = self.all_hosts_data[host]["ha_list"][ticket]
        agent = ":".join([ha["agent"].get(key) for key in ["standard", "provider", "ocftype"]])
        if agent == "ocf:ddn:Ticketer":
            return True
        return False

    def _nids_to_mgs(self, host, nid_strings):
        """
        :param host: host on which the target was seen.
        :param nid_strings: nids of a target
        :return: a ManagedMgs or raise ManagedMgs.DoesNotExist
        """
        if set(nid_strings) == set(["0@lo"]) or len(nid_strings) == 0:
            return ManagedMgs.objects.get(managedtargetmount__host=host)

        hosts = set()

        for nid_string in nid_strings:
            try:
                hosts.add(ManagedHost.get_by_nid(nid_string))
            except ManagedHost.DoesNotExist:
                pass

        if len(hosts) == 0:
            log.warning("nids_to_mgs: No unique NIDs among %s!" % nid_strings)

        try:
            mgs = ManagedMgs.objects.distinct().get(managedtargetmount__host__in=hosts)
        except ManagedMgs.MultipleObjectsReturned:
            log.error("Unhandled case: two MGSs have mounts on host(s) %s for nids %s" % (hosts, nid_strings))
            # TODO: detect and report the pathological case where someone has given
            # us two NIDs that refer to different hosts which both have a
            # targetmount for a ManagedMgs, but they're not the
            # same ManagedMgs.
            raise ManagedMgs.DoesNotExist

        return mgs

    def learn_primary_target(self, managed_target):

        primary_target = None
        managed_target.managedtargetmount_set.update(primary=False)
        for tm in managed_target.managedtargetmount_set.all():
            # We may well have scanned a subset of the hosts and so not have data for all the target mounts, if we
            # are rescanning we can know about targetmounts we didn't scan.
            if tm.host not in self.all_hosts_data:
                continue

            target_info = next(
                dev for dev in self.all_hosts_data[tm.host]["local_targets"] if dev["uuid"] == managed_target.uuid
            )
            local_nids = set(tm.host.lnet_configuration.get_nids())

            if not local_nids:
                raise NoNidsPresent("Host %s has no NIDS!" % tm.host)

            if "failover.node" in target_info["params"]:
                failover_nids = set(
                    normalize_nid(n) for nids in target_info["params"]["failover.node"] for n in nids.split(",")
                )

                if not bool(local_nids & failover_nids):
                    # In the case the current nids is not shown in the failover nids
                    # This target is considered primary and has been created with mkfs.lustre --failnode
                    # There isn't any other possibilities to have another primary defined
                    primary_target = tm
                    break
                elif target_info["mounted"]:
                    # In the case the target has been created with 'mkfs.lustre --servicenodes'
                    # If it is mounted, we use the current target as primary until we found a better candidate
                    primary_target = tm
            else:
                # If there are no failover nids then this must be the primary.
                primary_target = tm
                break

        if primary_target != None:
            log.info("Target %s has been set to primary" % (primary_target))
            primary_target.primary = True
            primary_target.save()
            ObjectCache.update(primary_target)

        return primary_target

    def is_valid(self):
        for host, host_data in self.all_hosts_data.items():
            try:
                assert isinstance(host_data, dict)
                assert "mgs_targets" in host_data
                assert "local_targets" in host_data
                # TODO: more thorough validation
                return True
            except AssertionError:
                return False

    def target_available_here(self, host, mgs, local_info):
        if local_info["mounted"]:
            return True

        target_nids = []
        if "failover.node" in local_info["params"]:
            for failover_str in local_info["params"]["failover.node"]:
                target_nids.extend(failover_str.split(","))

        if mgs:
            mgs_host = mgs.primary_host
            fs_name, target_name = local_info["name"].rsplit("-", 1)
            try:
                mgs_target_info = None
                for t in self.all_hosts_data[mgs_host]["mgs_targets"][fs_name]:
                    if t["name"] == local_info["name"]:
                        mgs_target_info = t
                if not mgs_target_info:
                    raise KeyError
            except KeyError:
                log.warning(
                    "Saw target %s on %s:%s which is not known to mgs %s"
                    % (local_info["name"], host, local_info["device_paths"], mgs_host)
                )
                return False
            primary_nid = mgs_target_info["nid"]
            target_nids.append(primary_nid)

        target_nids = set(normalize_nid(nid) for nid in target_nids)
        if set(host.lnet_configuration.get_nids()) & target_nids:
            return True
        else:
            return False

    def _target_find_mgs(self, host, local_info):
        # Build a list of MGS nids for this local target
        tgt_mgs_nids = []
        try:
            # NB I'm not sure whether tunefs.lustre will give me
            # one comma-separated mgsnode, or a series of mgsnode
            # settings, so handle both
            for n in local_info["params"]["mgsnode"]:
                tgt_mgs_nids.extend(n.split(","))
        except KeyError:
            # 'mgsnode' doesn't have to be present
            pass

        tgt_mgs_nids = set(normalize_nid(nid) for nid in tgt_mgs_nids)
        return self._nids_to_mgs(host, tgt_mgs_nids)

    def learn_target_mounts(self):
        for host, host_data in self.all_hosts_data.items():
            # We will compare any found target mounts to all known MGSs
            for local_info in host_data["local_targets"]:
                debug_id = (host, local_info["device_paths"][0], local_info["name"])
                targets = ManagedTarget.objects.filter(uuid=local_info["uuid"])
                if not targets.count():
                    log.warning("Ignoring %s:%s (%s), target unknown" % debug_id)
                    continue

                for target in targets:
                    if isinstance(target, FilesystemMember):
                        try:
                            mgs = self._target_find_mgs(host, local_info)
                        except ManagedMgs.DoesNotExist:
                            log.warning("Can't find MGS for target %s:%s (%s)" % debug_id)
                            continue
                    else:
                        mgs = None

                    if not self.target_available_here(host, mgs, local_info):
                        log.warning(
                            "Ignoring %s on %s, as it is not mountable on this host" % (local_info["name"], host)
                        )
                        continue

                    try:
                        log.info("Target %s seen on %s" % (target, host))
                        volumenode = self._get_volume_node(host, local_info["device_paths"])
                        (tm, created) = ManagedTargetMount.objects.get_or_create(
                            target=target, host=host, volume_node=volumenode
                        )
                        if created:
                            if local_info["mounted"]:
                                tm.mount_point = local_info.get("mount_point")

                            tm.save()
                            log.info(
                                "Learned association %d between %s and host %s" % (tm.id, local_info["name"], host)
                            )
                            self._learn_event(host, tm)
                            ObjectCache.add(ManagedTargetMount, tm)

                        if local_info["mounted"]:
                            target.state = "mounted"
                            target.active_mount = tm

                            label = local_info.get("ha_label")

                            if label:
                                target.ha_label = label
                                target.immutable_state = False

                            target.save()
                            ObjectCache.update(target)

                    except NoNidsPresent:
                        log.warning("Cannot set up target %s on %s until LNet is running" % (local_info["name"], host))

    def _get_volume_node(self, host, paths):
        device_hosts = DeviceHost.objects.filter(paths__0__in=paths, host=host)
        if not device_hosts.count():
            log.warning("No device nodes detected matching paths %s on host %s" % (paths, host))
            raise DeviceHost.DoesNotExist
        else:
            if device_hosts.count() > 1:
                # On a sanely configured server you wouldn't have more than one, but if
                # e.g. you formatted an mpath device and then stopped multipath, you
                # might end up seeing the two underlying devices.  So we cope, but warn.
                log.warning(
                    "DetectScan: Multiple DeviceHosts found for paths %s on host %s, using %s"
                    % (paths, host, device_hosts[0].paths[0])
                )
            return device_hosts[0]

    def learn_fs_targets(self):
        for host, host_data in self.all_hosts_data.items():
            for local_info in host_data["local_targets"]:
                if not local_info["mounted"]:
                    log.warning("Ignoring unmounted target %s on host %s" % (local_info["name"], host))
                    continue

                name = local_info["name"]
                device_node_paths = local_info["device_paths"]
                uuid = local_info["uuid"]

                if name.find("-MDT") != -1:
                    klass = ManagedMdt
                elif name.find("-OST") != -1:
                    klass = ManagedOst
                elif name == "MGS":
                    continue
                else:
                    raise NotImplementedError()

                try:
                    mgs = self._target_find_mgs(host, local_info)
                except ManagedMgs.DoesNotExist:
                    log.warning("Can't find MGS for target %s on %s" % (name, host))
                    continue

                fsname, index_str = re.search("([\w\-]+)-(\w)+", name).groups()
                index = int(index_str, 16)

                # Create Filesystem objects if we've not seen this FS before.
                (filesystem, created) = ManagedFilesystem.objects.get_or_create(name=fsname, mgs=mgs)
                self.discovered_filesystems.add(filesystem)

                if created:
                    self.created_filesystems.append(filesystem)
                    filesystem.immutable_state = True
                    filesystem.save()
                    log.info("Found filesystem '%s'" % fsname)
                    ObjectCache.add(ManagedFilesystem, filesystem)

                try:
                    klass.objects.get(uuid=uuid)
                except ManagedTarget.DoesNotExist:
                    # Fall through, no targets with that name exist on this MGS
                    device_host = self._get_volume_node(host, device_node_paths)
                    target = klass(
                        uuid=uuid,
                        name=name,
                        filesystem=filesystem,
                        state="mounted",
                        device=device_host.device,
                        index=index,
                        immutable_state=True,
                    )
                    target.save()
                    log.debug("%s" % [mt.name for mt in ManagedTarget.objects.all()])
                    log.info("%s %s %s" % (mgs.id, name, device_node_paths))
                    log.info("Found %s %s" % (klass.__name__, name))
                    self.created_targets.append(target)
                    ObjectCache.add(ManagedTarget, target.managedtarget_ptr)

    def _learn_event(self, host, learned_item):
        from logging import INFO

        LearnEvent.register_event(severity=INFO, alert_item=host, learned_item=learned_item)

    def learn_mgs_targets(self):
        for host, host_data in self.all_hosts_data.items():
            mgs_local_info = None
            for device in host_data["local_targets"]:
                device_host = DeviceHost.objects.get(device=device, fqdn=host.fqdn)
                name = device_host.fs_label
                mounted = device_host.mount_path
                if name == "MGS" and mounted == True:
                    mgs_local_info = device
            if not mgs_local_info:
                log.debug("No MGS found on host %s" % host)
                continue

            try:
                ManagedMgs.objects.get(uuid=mgs_local_info["uuid"])
            except ManagedMgs.DoesNotExist:
                try:
                    device_host = self._get_volume_node(host, mgs_local_info["device_paths"])
                except DeviceHost.DoesNotExist:
                    continue

                log.info("Learned MGS %s (%s)" % (host, mgs_local_info["device_paths"][0]))
                # We didn't find an existing ManagedMgs referring to
                # this LUN, create one
                mgs = ManagedMgs(
                    uuid=mgs_local_info["uuid"],
                    state="mounted",
                    device=device_host.device,
                    name="MGS",
                    immutable_state=True,
                )
                mgs.save()
                self.created_mgss.append(mgs)
                ObjectCache.add(ManagedTarget, mgs.managedtarget_ptr)
