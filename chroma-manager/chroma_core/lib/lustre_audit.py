#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.models import ManagedTargetMount

import settings

from chroma_core.models.alert import TargetRecoveryAlert, HostContactAlert
from chroma_core.models.event import LearnEvent
from chroma_core.models.target import ManagedMgs, ManagedMdt, ManagedOst, ManagedTarget, FilesystemMember, TargetRecoveryInfo
from chroma_core.models.host import ManagedHost, Nid, VolumeNode
from chroma_core.models.filesystem import ManagedFilesystem
from django.db import transaction
import functools

# django doesn't abstract this
import MySQLdb as Database

audit_log = settings.setup_log('audit')


def nids_to_mgs(host, nid_strings):
    """nid_strings: nids of a target.  host: host on which the target was seen.
    Return a ManagedMgs or raise ManagedMgs.DoesNotExist"""
    if set(nid_strings) == set(["0@lo"]) or len(nid_strings) == 0:
        return ManagedMgs.objects.get(targetmount__host = host)

    from django.db.models import Count
    nids = Nid.objects.values('nid_string').filter(nid_string__in = nid_strings).annotate(Count('id'))
    unique_nids = [n['nid_string'] for n in nids if n['id__count'] == 1]

    if len(unique_nids) == 0:
        audit_log.warning("nids_to_mgs: No unique NIDs among %s!" % nids)
    hosts = list(ManagedHost.objects.filter(lnetconfiguration__nid__nid_string__in = unique_nids).distinct())
    try:
        mgs = ManagedMgs.objects.distinct().get(managedtargetmount__host__in = hosts)
    except ManagedMgs.MultipleObjectsReturned:
        audit_log.error("Unhandled case: two MGSs have mounts on host(s) %s for nids %s" % (hosts, unique_nids))
        # TODO: detect and report the pathological case where someone has given
        # us two NIDs that refer to different hosts which both have a
        # targetmount for a ManagedMgs, but they're not the
        # same ManagedMgs.
        raise ManagedMgs.DoesNotExist

    return mgs


def normalize_nid(string):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow
       direct comparisons between NIDs"""
    if string[-4:] == "@tcp":
        string += "0"

    # remove _ from nids (i.e. @tcp_0 -> @tcp0
    i = string.find("_")
    if i > -1:
        string = string[:i] + string[i + 1:]

    return string


def normalize_nids(nid_list):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow
       direct comparisons between NIDs"""
    return [normalize_nid(n) for n in nid_list]


class NoLNetInfo(Exception):
    pass


class UpdateScan(object):
    def __init__(self):
        self.audited_mountables = {}
        self.host = None
        self.host_data = None

    def is_valid(self):
        try:
            assert(isinstance(self.host_data, dict))
            assert('lnet_up' in self.host_data)
            assert('lnet_loaded' in self.host_data)
            assert('mounts' in self.host_data)
            assert('metrics' in self.host_data)
            assert('resource_locations' in self.host_data)
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    @transaction.commit_on_success
    def audit_host(self):
        if isinstance(self.host_data, Exception):
            audit_log.error("exception contacting %s: %s" % (self.host, self.host_data))
            contact = False
        elif not self.is_valid():
            audit_log.error("invalid output from %s: %s" % (self.host, self.host_data))
            contact = False
        else:
            contact = True

            # Get state of Client objects
            #self.learn_clients()

            # Forgotten entities should be ignored so that they're
            # not "rediscovered" or monitored.
            self.cull_forgotten_data()

            # Older agents don't send this list
            if 'capabilities' in self.host_data:
                self.learn_unmanaged_host()

            self.update_lnet()
            self.update_resource_locations()
            self.update_target_mounts()

        HostContactAlert.notify(self.host, not contact)

        if contact:
            from datetime import datetime
            ManagedHost.objects.filter(pk = self.host.pk).update(last_contact = datetime.utcnow())

        return contact

    def run(self, host_id, started_at, host_data):
        host = ManagedHost.objects.get(pk=host_id)
        self.started_at = started_at
        self.host = host
        self.host_data = host_data
        audit_log.debug("UpdateScan.run: %s" % self.host)

        contact = self.audit_host()
        self.store_metrics()

        return contact

    def cull_forgotten_data(self):
        mounted_uuids = dict([(m['fs_uuid'], m) for m in self.host_data['mounts']])
        forgotten_uuids = dict([(mt.uuid, mt) for mt in ManagedTarget._base_manager.filter(state = 'forgotten')])

        for forgotten_uuid in forgotten_uuids:
            if forgotten_uuid in mounted_uuids:
                audit_log.debug("Culling forgotten ManagedTarget: %s" % forgotten_uuids[forgotten_uuid].name)
                self.host_data['mounts'].remove(mounted_uuids[forgotten_uuid])

    def _audited_lnet_state(self):
        return {(False, False): 'lnet_unloaded',
                (True, False): 'lnet_down',
                (True, True): 'lnet_up'}[(self.host_data['lnet_loaded'],
                                          self.host_data['lnet_up'])]

    def learn_unmanaged_host(self):
        # FIXME: What to do if we split out rsyslog into an optional
        # package?  Rename it to configure_rsyslog?
        def _agent_can_manage(cap_list):
            return len([c for c in cap_list if "manage_" in c]) > 0

        # If the agent is capable of managing things, we don't want to
        # mess around in here.
        if _agent_can_manage(self.host_data['capabilities']):
            return False

        # If a host is monitor-only, then we can't effect any changes
        # on its state via the agent.  We still want to be aware of state
        # changes as they happen, though.  There are a few scenarios
        # to account for:
        #
        # 1. If we encounter an unmanaged host which is presenting a
        #    greater number of mounted targets than what we already
        #    know about, then it's a good trigger for running a
        #    DetectTargetsJob.
        #
        # TODO: This is a terrible way to do it.  The right way to do
        # is probably to compare the set of known mount uuids vs. the
        # audited mounts.  Commenting it out for now, as there are
        # concerns about automatic initiation of DetectTargetsJobs anyhow.
        #if len(self.host.managedtargetmount_set.all()) < len(self.host_data['mounts']):
            # Only try this if LNet is actually up and running. I don't
            # know why there would be more mounts than we already know about
            # if this weren't the case, but there's no point in running
            # useless jobs if there aren't Lustre targets to find.
            #
            # NB: This may result in a bit of flailing if not all of
            # the hosts are in 'lnet_up'.  I'm undecided as to whether
            # this is a good thing or if the dependency should be relaxed.
            #from chroma_core.models import DetectTargetsJob
            #if self.host.state == "lnet_up":
            #    audit_log.debug("Running DetectTargetsJob")
            #    job = DetectTargetsJob()
            #    StateManager().add_job(job)

        # Finally, ensure that the host is flagged as immutable, from
        # our perspective.
        if not self.host.immutable_state:
            audit_log.debug("Setting immutable_state flag on %s" % self.host)
            self.host.immutable_state = True
            self.host.save()

    def update_lnet(self):
        # Update LNet status
        from chroma_core.lib.state_manager import StateManager
        StateManager.notify_state(self.host.downcast(),
                                  self.started_at,
                                  self._audited_lnet_state(),
                                  ['lnet_unloaded', 'lnet_down', 'lnet_up'])

    def update_target_mounts(self):
        # Loop over all mountables we expected on this host, whether they
        # were actually seen in the results or not.
        mounted_uuids = dict([(m['fs_uuid'], m) for m in self.host_data['mounts']])
        for target_mount in ManagedTargetMount.objects.filter(host = self.host):

            # Mounted-ness
            # ============
            mounted_locally = target_mount.target.uuid in mounted_uuids

            # Recovery status
            # ===============
            if mounted_locally:
                mount_info = mounted_uuids[target_mount.target.uuid]
                recovery_status = mount_info["recovery_status"]
            else:
                recovery_status = {}

            # Update to active_mount and alerts for monitor-only
            # targets done here instead of resource_locations
            if target_mount.target.immutable_state:
                target = target_mount.target
                if mounted_locally:
                    target.set_active_mount(target_mount)
                elif not mounted_locally and target.active_mount == target_mount:
                    target.set_active_mount(None)

            if target_mount.target.active_mount == None:
                TargetRecoveryInfo.update(target_mount.target, {})
                TargetRecoveryAlert.notify(target_mount.target, False)
            elif mounted_locally:
                recovering = TargetRecoveryInfo.update(target_mount.target, recovery_status)
                TargetRecoveryAlert.notify(target_mount.target, recovering)

    def update_resource_locations(self):
        if self.host_data['resource_locations'] == None:
            # None here means that it was not possible to obtain a
            # list from corosync: corosync may well be absent if
            # we're monitoring a non-chroma-managed monitor-only
            # system.  But if there are managed mounts
            # then this is a problem.
            from django.db.models import Q
            if ManagedTargetMount.objects.filter(~Q(target__immutable_state = True), host = self.host).count() > 0:
                audit_log.error("Got no resource_locations from host %s, but there are chroma-configured mounts on that server!" % self.host)
            return

        for resource_name, node_name in self.host_data['resource_locations'].items():
            try:
                try:
                    # Parse a resource name like "MGS_2"
                    target_name, target_pk = resource_name.rsplit("_", 1)
                except ValueError:
                    audit_log.warning("Malformed resource name '%s'" % resource_name)
                    continue
                target = ManagedTarget.objects.get(name = target_name, pk = target_pk).downcast()
            except ManagedTarget.DoesNotExist:
                #audit_log.warning("Resource %s on host %s is not a known target" % (resource_name, self.host))
                continue

            # If we're operating on a Managed* rather than a purely monitored target
            if not target.immutable_state:
                if node_name == None:
                    active_mount = None
                else:
                    try:
                        host = ManagedHost.objects.get(nodename = node_name)
                        try:
                            active_mount = ManagedTargetMount.objects.get(target = target, host = host)
                        except ManagedTargetMount.DoesNotExist:
                            audit_log.warning("Resource for target '%s' is running on host '%s', but there is no such TargetMount" % (target, host))
                            active_mount = None
                    except ManagedHost.DoesNotExist:
                        audit_log.warning("Resource location node '%s' does not match any Host" % (node_name))
                        active_mount = None

                target.set_active_mount(active_mount)

                state = ['unmounted', 'mounted'][active_mount != None]
                from chroma_core.lib.state_manager import StateManager
                StateManager.notify_state(target, self.started_at, state, ['mounted', 'unmounted'])

    def store_lustre_target_metrics(self, target_name, metrics):
        # TODO: Re-enable MGS metrics storage if it turns out it's useful.
        if target_name == "MGS":
            return 0

        try:
            target = ManagedTarget.objects.get(name=target_name,
                                        managedtargetmount__host=self.host).downcast()
        except ManagedTarget.DoesNotExist:
            # Unknown target -- ignore metrics
            audit_log.warning("Discarding metrics for unknown target: %s" % target_name)
            return 0

        # Synthesize the 'client_count' metric (assumes one MDT per filesystem)
        if isinstance(target, ManagedMdt):
            metrics['client_count'] = metrics['num_exports'] - 1

        if target.state == 'forgotten':
            return 0
        else:
            return target.metrics.update(metrics, self.update_time)

    def store_node_metrics(self, metrics):
        return self.host.downcast().metrics.update(metrics, self.update_time)

    def catch_metrics_deadlocks(fn):
        # This decorator is specific to catching deadlocks which may occur
        # during an r3d update.  Ideally, these shouldn't happen at all, but
        # if they do they shouldn't be fatal.  In any case, we need to log
        # warnings so we can keep track of this and figure out if it's really
        # a problem, and if it is, whether to fix it in code or in db tuning.
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Database.OperationalError, e:
                if e[0] == 1213:
                    audit_log.warn("Caught deadlock on metrics update; discarding metrics and continuing")
                    return 0

                raise e
        return wrapper

    @catch_metrics_deadlocks
    @transaction.commit_on_success
    def store_metrics(self):
        """
        Pass the received metrics into the metrics library for storage.
        """
        raw_metrics = self.host_data['metrics']['raw']
        count = 0

        if not hasattr(self, 'update_time'):
            self.update_time = None

        try:
            node_metrics = raw_metrics['node']
            try:
                node_metrics['lnet'] = raw_metrics['lustre']['lnet']
            except KeyError:
                pass

            count += self.store_node_metrics(node_metrics)
        except KeyError:
            pass

        try:
            for target in raw_metrics['lustre']['target']:
                target_metrics = raw_metrics['lustre']['target'][target]
                count += self.store_lustre_target_metrics(target, target_metrics)
        except KeyError:
            pass

        return count


class DetectScan(object):
    def __init__(self):
        self.raw_data = None
        self.target_locations = None

    @transaction.commit_on_success
    def run(self, host_id, host_data, all_hosts_data):
        host = ManagedHost.objects.get(pk = host_id)
        # Inside our audit update transaction, check that the host isn't
        # deleted to avoid raising alerts for a deleted host
        if not host.not_deleted:
            return

        self.host = host
        self.host_data = host_data
        self.all_hosts_data = all_hosts_data

        if isinstance(host_data, Exception):
            audit_log.error("exception contacting %s: %s" % (self.host, host_data))
            contact = False
        elif not self.is_valid():
            audit_log.error("invalid output from %s: %s" % (self.host, host_data))
            contact = False
        else:
            contact = True

            # Create Filesystem and Target objects
            self.learn_mgs_info()

            # Create TargetMount objects
            self.learn_target_mounts()

                # Configuration params
                # ====================
 #               if mounted_locally:
 #                   TargetParam.update_params(target_mount.target, mount_info['params'])

        return contact

    def is_primary(self, local_target_info):
        if self.host.lnetconfiguration.state != 'nids_known':
            raise NoLNetInfo("Cannot setup target %s without LNet info" % local_target_info['name'])

        local_nids = set(self.host.lnetconfiguration.get_nids())

        if not 'failover.node' in local_target_info['params']:
            # If the target has no failover nodes, then it is accessed by only
            # one (primary) host, i.e. this one
            primary = True
        elif len(local_nids) > 0:
            # We know this hosts's nids, and which nids are secondaries for this target,
            # so we can work out whether we're primary by a process of elimination
            failover_nids = []
            for failover_str in local_target_info['params']['failover.node']:
                failover_nids.extend(failover_str.split(","))
            failover_nids = set(normalize_nids(failover_nids))

            primary = not (local_nids & failover_nids)

        return primary

    def is_valid(self):
        try:
            assert(isinstance(self.host_data, dict))
            assert('mgs_targets' in self.host_data)
            assert('local_targets' in self.host_data)
            # TODO: more thorough validation
            return True
        except AssertionError:
            return False

    def learn_mgs(self, mgs_local_info):
        try:
            mgs = ManagedMgs.objects.get(uuid = mgs_local_info['uuid'])
            try:
                tm = ManagedTargetMount.objects.get(target = mgs, host = self.host)
            except ManagedTargetMount.DoesNotExist:
                volumenode = self.get_volume_node_for_target(None, self.host, mgs_local_info['devices'])
                primary = self.is_primary(mgs_local_info)
                tm = ManagedTargetMount.objects.create(
                        immutable_state = True,
                        target = mgs,
                        host = self.host,
                        primary = primary,
                        volume_node = volumenode)
        except ManagedMgs.DoesNotExist:
            # Only do this for primary mount location
            # Otherwise would risk seeing an MGS somewhere it's not actually
            # used and assuming that that was the primary location.
            if not self.is_primary(mgs_local_info):
                return None

            # The MGS has to be mounted because that's the only way we
            # can tell what its primary NID is
            if not mgs_local_info['mounted']:
                audit_log.warning("Cannot detect MGS on %s because it is not mounted" % self.host)
                return None

            try:
                mgs = ManagedMgs.objects.get(managedtargetmount__host = self.host)
                raise RuntimeError("Multiple MGSs on host %s" % self.host)
            except ManagedMgs.DoesNotExist:
                pass

            volumenode = self.get_volume_node_for_target(None, self.host,
                                                   mgs_local_info['devices'])

            primary = self.is_primary(mgs_local_info)

            # We didn't find an existing ManagedMgs referring to
            # this LUN, create one
            mgs = ManagedMgs(uuid = mgs_local_info['uuid'],
                             state = "mounted", lun = volumenode.volume,
                             name = "MGS", immutable_state = True)
            mgs.save()
            audit_log.info("Learned MGS on %s" % self.host)
            self.learn_event(mgs)

            tm = ManagedTargetMount.objects.create(
                    target = mgs,
                    host = self.host,
                    primary = primary,
                    volume_node = volumenode)
            audit_log.info("Learned MGS mount %s" % (tm.host))
            self.learn_event(tm)

        return mgs

    def target_available_here(self, mgs, local_info):
        target_nids = []
        if 'failover.node' in local_info['params']:
            for failover_str in local_info['params']['failover.node']:
                target_nids.extend(failover_str.split(","))
        mgs_host = mgs.primary_server()
        fs_name, target_name = local_info['name'].rsplit("-", 1)
        try:
            mgs_target_info = None
            for t in self.all_hosts_data[mgs_host]['mgs_targets'][fs_name]:
                if t['name'] == local_info['name']:
                    mgs_target_info = t
            if not mgs_target_info:
                raise KeyError
        except KeyError:
            audit_log.warning("Saw target %s on %s:%s which is not known to mgs %s" % (local_info['name'], self.host, local_info['devices'], mgs_host))
            return False
        primary_nid = mgs_target_info['nid']
        target_nids.append(primary_nid)

        target_nids = set(normalize_nids(target_nids))
        if set(self.host.lnetconfiguration.get_nids()) & target_nids:
            return True
        else:
            return False

    def learn_target_mounts(self):
        # We will compare any found target mounts to all known MGSs
        for local_info in self.host_data['local_targets']:
            # We learned all targetmounts for MGSs in learn_mgs
            if local_info['name'] == 'MGS':
                continue

            # Build a list of MGS nids for this local target
            tgt_mgs_nids = []
            try:
                # NB I'm not sure whether tunefs.lustre will give me
                # one comma-separated mgsnode, or a series of mgsnode
                # settings, so handle both
                for n in local_info['params']['mgsnode']:
                    tgt_mgs_nids.extend(n.split(","))
            except KeyError:
                # 'mgsnode' doesn't have to be present
                pass
            tgt_mgs_nids = set(normalize_nids(tgt_mgs_nids))

            try:
                mgs = nids_to_mgs(self.host, tgt_mgs_nids)
            except ManagedMgs.DoesNotExist:
                audit_log.warning("Can't find MGS for target with nids %s" % tgt_mgs_nids)
                continue

            if not self.target_available_here(mgs, local_info):
                audit_log.warning("Ignoring %s on %s, as it is not mountable on this host" % (local_info['name'], self.host))
                continue

            # FIXME: we ought to make sure get_or_create_target is only called
            # if we definitely have a primary mount for the target to avoid
            # putting something invalid in the database

            # TODO: detect case where we find a targetmount that matches one
            # which already exists for a different target, where the other target
            # has no name -- in this case we are overlapping with a blank target
            # that was created during configuration.
            target = self.get_or_create_target(mgs, local_info)
            if not target:
                continue

            try:
                primary = self.is_primary(local_info)
                volumenode = self.get_volume_node_for_target(target, self.host, local_info['devices'])
                (tm, created) = ManagedTargetMount.objects.get_or_create(target = target,
                        host = self.host, primary = primary,
                        volume_node = volumenode)
                if created:
                    tm.immutable_state = True
                    tm.save()
                    audit_log.info("Learned association %d between %s and host %s" % (tm.id, local_info['name'], self.host))
                    self.learn_event(tm)
            except NoLNetInfo:
                audit_log.warning("Cannot set up target %s on %s until LNet is running" % (local_info['name'], self.host))

    def get_volume_node_for_target(self, target, host, paths):
        lun_nodes = VolumeNode.objects.filter(path__in = paths, host = host)
        if lun_nodes.count() == 0:
            raise RuntimeError("No device nodes detected matching paths %s on host %s" % (paths, host))
        else:
            if lun_nodes.count() > 1:
                # On a sanely configured server you wouldn't have more than one, but if
                # e.g. you formatted an mpath device and then stopped multipath, you
                # might end up seeing the two underlying devices.  So we cope, but warn.
                audit_log.warning("DetectScan: Multiple VolumeNodes found for paths %s on host %s, using %s" % (paths, host, lun_nodes[0].path))
            return lun_nodes[0]

    def get_or_create_target(self, mgs, local_info):
        name = local_info['name']
        device_node_paths = local_info['devices']
        uuid = local_info['uuid']

        if name.find("-MDT") != -1:
            klass = ManagedMdt
        elif name.find("-OST") != -1:
            klass = ManagedOst

        import re
        fsname = re.search("([\w\-]+)-\w+", name).group(1)
        try:
            filesystem = ManagedFilesystem.objects.get(name = fsname, mgs = mgs)
        except ManagedFilesystem.DoesNotExist:
            audit_log.warning("Encountered target (%s) for unknown filesystem %s on mgs %s" % (name, fsname, mgs.primary_server()))
            return None

        try:
            # Is it an already detected or configured target?
            target_mount = ManagedTargetMount.objects.get(
                    volume_node = self.get_volume_node_for_target(None, self.host, device_node_paths), host = self.host)
            target = target_mount.target
            if target.name == None:
                target.name = name
                target.save()
                audit_log.info("Learned name for configured target %s" % (target))

            return target
        except ManagedTargetMount.DoesNotExist:
            # We are detecting a target anew, or detecting a new mount for an already-named target
            candidates = ManagedTarget.objects.filter(name = name)
            for target in candidates:
                target = target.downcast()
                audit_log.debug("candidate: %s %s" % (target, target.__class__))
                audit_log.debug("candidate: %s %s" % (isinstance(target.downcast(), FilesystemMember), target.filesystem.mgs.downcast() == mgs))
                if isinstance(target.downcast(), FilesystemMember) and target.filesystem.mgs.downcast() == mgs:
                    return target

            # Fall through, no targets with that name exist on this MGS
            volumenode = self.get_volume_node_for_target(None, self.host,
                                                   device_node_paths)
            target = klass(uuid = uuid, name = name, filesystem = filesystem,
                           state = "mounted", volume = volumenode.volume,
                           immutable_state = True)
            target.save()
            audit_log.debug("%s" % [mt.name for mt in ManagedTarget.objects.all()])
            audit_log.info("%s %s %s" % (mgs.id, name, device_node_paths))
            audit_log.info("Learned %s %s" % (klass.__name__, name))
            self.learn_event(target)

            return target

    def learn_event(self, learned_item):
        from logging import INFO
        LearnEvent(severity = INFO, host = self.host, learned_item = learned_item).save()

    def learn_clients(self):
        pass
        #for mount_point, client_info in self.host_data['client_mounts'].items():
            # Find the MGS
            #try:
            #    # Lustre lets you use either
            #    # a comma or a colon as a delimiter
            #    nids = re.split("[:,]", client_info['nid'])
            #    client_mgs_nids = set(normalize_nids(nids))
            #    mgs = nids_to_mgs(self.host, client_mgs_nids)
            #except ManagedMgs.DoesNotExist:
            #    audit_log.warning("Ignoring client mount for unknown mgs %s" % client_info['nid'])
            #    continue

            # Find the filesystem
            #try:
            #    fs = ManagedFilesystem.objects.get(name = client_info['filesystem'], mgs = mgs)
            #except ManagedFilesystem.DoesNotExist:
            #    audit_log.warning("Ignoring client mount for unknown filesystem '%s' on %s" % (client_info['filesystem'], self.host))
            #    continue

            # TODO: sort out client monitoring
            # Instantiate Client
            #(client, created) = Client.objects.get_or_create(
            #        host = self.host, mount_point = mount_point, filesystem = fs)
            #if created:
            #    audit_log.info("Learned client %s" % client)
            #    self.learn_event(client)

            #self.audited_mountables[client.downcast()] = client_info['mounted']

    def learn_mgs_info(self):
        found_mgs = False
        for volume in self.host_data['local_targets']:
            if volume['name'] == "MGS":
                found_mgs = True
                mgs_local_info = volume
        if not found_mgs:
            audit_log.debug("No MGS found on host %s" % self.host)
            return

        # Learn an MGS target and a TargetMount for this host
        mgs = self.learn_mgs(mgs_local_info)
        if not mgs:
            return

        forgotten_fs_names = [f.name for f in ManagedFilesystem._base_manager.filter(state = 'forgotten')]

        # Create Filesystem objects for all those in this MGS which aren't
        # being ignored.
        for fs_name, targets in self.host_data['mgs_targets'].items():
            if fs_name in forgotten_fs_names:
                audit_log.debug("Ignoring forgotten fs on DetectScan: %s" % fs_name)
                continue

            (fs, created) = ManagedFilesystem.objects.get_or_create(name = fs_name, mgs = mgs)
            if created:
                fs.immutable_state = True
                fs.save()
                audit_log.info("Learned filesystem '%s'" % fs_name)
                self.learn_event(fs)
