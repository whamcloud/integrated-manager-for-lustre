#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.shortcuts import get_object_or_404

from django.contrib.contenttypes.models import ContentType
from chroma_core.lib.state_manager import StateManager

from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs
from chroma_core.models import ManagedFilesystem, ManagedTargetMount, ManagedHost
from chroma_core.models import Command
from chroma_api.requesthandler import RequestHandler, APIResponse
import chroma_core.lib.conf_param

import chroma_core.lib.util
import chroma_api.target
import chroma_api.configureapi


def create_fs(mgs_id, name, conf_params):
        mgs = ManagedMgs.objects.get(id=mgs_id)
        fs = ManagedFilesystem(mgs=mgs, name = name)
        fs.save()

        for key, value in conf_params:
            chroma_core.lib.conf_param.set_conf_param(fs, key, value)

        return fs


class FilesystemHandler(RequestHandler):
    # TODO: common PUT code for handling conf params on targets and filesystems
    def put(self, request, id):
        filesystem = get_object_or_404(ManagedFilesystem, pk = id).downcast()
        try:
            conf_params = request.data['conf_params']
        except KeyError:
            return APIResponse(None, 400)

        # TODO: validate the parameters before trying to set any of them

        for k, v in conf_params.items():
            chroma_core.lib.conf_param.set_conf_param(filesystem, k, v)

    def post(self, request, fsname, mgt_id, mgt_lun_id, mdt_lun_id, ost_lun_ids, conf_params):
        # mgt_id and mgt_lun_id are mutually exclusive:
        # * mgt_id is a PK of an existing ManagedMgt to use
        # * mgt_lun_id is a PK of a Lun to use for a new ManagedMgt
        assert bool(mgt_id) != bool(mgt_lun_id)

        if not mgt_id:
            mgt = chroma_api.target.create_target(mgt_lun_id, ManagedMgs, name="MGS")
            mgt_id = mgt.pk
        else:
            mgt_lun_id = ManagedMgs.objects.get(pk = mgt_id).get_lun()

        # This is a brute safety measure, to be superceded by
        # some appropriate validation that gives a helpful
        # error to the user.
        all_lun_ids = [mgt_lun_id] + [mdt_lun_id] + ost_lun_ids
        # Test that all values in all_lun_ids are unique
        assert len(set(all_lun_ids)) == len(all_lun_ids)

        from django.db import transaction
        with transaction.commit_on_success():
            fs = create_fs(mgt_id, fsname, conf_params)
            chroma_api.target.create_target(mdt_lun_id, ManagedMdt, filesystem = fs)
            osts = []
            for lun_id in ost_lun_ids:
                osts.append(chroma_api.target.create_target(lun_id, ManagedOst, filesystem = fs))
        # Important that a commit happens here so that the targets
        # land in DB before the set_state jobs act upon them.

        command = Command.set_state(fs, 'available', "Creating filesystem %s" % fsname)

        return APIResponse({
            'filesystem': {'id': fs.id},
            'command': command.to_dict()
            }, 201)

    def get(self, request, id = None):
        if id:
            filesystem = get_object_or_404(ManagedFilesystem, pk = id)
            osts = ManagedOst.objects.filter(filesystem = filesystem)
            no_of_ost = osts.count()
            no_of_oss = len(set([tm.host for tm in ManagedTargetMount.objects.filter(target__in = osts)]))
            no_of_oss = ManagedHost.objects.filter(managedtargetmount__target__in = osts).distinct().count()
            mds_hostname = ''
            mds_status = ''
            # if FS is created but MDT is no created we still want to display fs in list
            try:
                mds = ManagedMdt.objects.get(filesystem = filesystem).primary_server()
                mds_hostname = mds.pretty_name()
                mds_status = mds.status_string()
            except ManagedMdt.DoesNotExist:
                pass
            try:
                fskbytesfree = 0
                fskbytestotal = 0
                fsfilesfree = 0
                fsfilestotal = 0
                inodedata = filesystem.metrics.fetch_last(ManagedMdt, fetch_metrics=["filesfree", "filestotal"])
                diskdata = filesystem.metrics.fetch_last(ManagedOst, fetch_metrics=["kbytesfree", "kbytestotal"])
                if diskdata:
                    fskbytesfree = diskdata[1]['kbytesfree']
                    fskbytestotal = diskdata[1]['kbytestotal']
                if inodedata:
                    fsfilesfree = inodedata[1]['filesfree']
                    fsfilestotal = inodedata[1]['filestotal']
            except:
                    pass

            return {'fsname': filesystem.name,
                    'status': filesystem.status_string(),
                    'noofoss': no_of_oss,
                    'noofost': no_of_ost,
                    'mgs_hostname': filesystem.mgs.primary_server().pretty_name(),
                    'mds_hostname': mds_hostname,
                    'mdsstatus': mds_status,
                    # FIXME: the API should not be formatting these, leave it to the presentation layer
                    'bytes_total': chroma_core.lib.util.sizeof_fmt((fskbytestotal * 1024)),
                    'bytes_free': chroma_core.lib.util.sizeof_fmt((fskbytesfree * 1024)),
                    'bytes_used': chroma_core.lib.util.sizeof_fmt(((fskbytestotal - fskbytesfree) * 1024)),
                    'inodes_free': fsfilesfree,
                    'inodes_total': fsfilestotal,
                    'inodes_used': (fsfilestotal - fsfilesfree),
                    'conf_params': chroma_core.lib.conf_param.get_conf_params(filesystem),
                    'id': filesystem.id,
                    'content_type_id': ContentType.objects.get_for_model(filesystem).id}
        else:
            filesystems = []
            mds_hostname = ''
            for filesystem in ManagedFilesystem.objects.all():
                osts = ManagedOst.objects.filter(filesystem = filesystem)
                no_of_ost = osts.count()
                no_of_oss = len(set([tm.host for tm in ManagedTargetMount.objects.filter(target__in = osts)]))
                no_of_oss = ManagedHost.objects.filter(managedtargetmount__target__in = osts).distinct().count()
                # if FS is created but MDT is no created we still want to display fs in list
                try:
                    mds_hostname = ManagedMdt.objects.get(filesystem = filesystem).primary_server().pretty_name()
                except:
                    pass

                fskbytesfree = 0
                fskbytestotal = 0
                fsfilesfree = 0
                fsfilestotal = 0
                try:
                    inodedata = filesystem.metrics.fetch_last(ManagedMdt, fetch_metrics = ["filesfree", "filestotal"])
                    diskdata = filesystem.metrics.fetch_last(ManagedOst, fetch_metrics = ["kbytesfree", "kbytestotal"])
                    if diskdata:
                        fskbytesfree = diskdata[1]['kbytesfree']
                        fskbytestotal = diskdata[1]['kbytestotal']
                    if inodedata:
                        fsfilesfree = inodedata[1]['filesfree']
                        fsfilestotal = inodedata[1]['filestotal']
                except:
                    pass

                # FIXME: fsid and fsname are bad names, they should be 'id' and 'name'
                filesystems.append({'fsid': filesystem.id,
                                    'fsname': filesystem.name,
                                    'status': filesystem.status_string(),
                                    'available_transitions': StateManager.available_transitions(filesystem),
                                    'noofoss': no_of_oss,
                                    'noofost': no_of_ost,
                                    'mgs_hostname': filesystem.mgs.primary_server().pretty_name(),
                                    'mds_hostname': mds_hostname,
                                    # FIXME: the API should not be formatting these, leave it to the presentation layer
                                    'kbytesused': chroma_core.lib.util.sizeof_fmt((fskbytestotal * 1024)),
                                    'kbytesfree': chroma_core.lib.util.sizeof_fmt((fskbytesfree * 1024)),
                                    'conf_params': chroma_core.lib.conf_param.get_conf_params(filesystem),
                                    'id': filesystem.id,
                                    'content_type_id': ContentType.objects.get_for_model(filesystem).id})

            return filesystems
