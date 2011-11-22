
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import transaction


def _validate_conf_params(conf_params):
    from configure.lib.conf_param import all_params
    for key, val in conf_params.items():
        try:
            model_klass, param_value_obj, help_text = all_params[key]
            param_value_obj.validate(val)
        except KeyError:
            # Let users set params we've never heard of, good luck.
            pass


def _find_or_create_target(klass, mounts, **kwargs):
    from configure.models import ManagedHost, ManagedTargetMount

    target = None
    for m in mounts:
        host = ManagedHost.objects.get(address = m['host'])
        try:
            mount = ManagedTargetMount.objects.get(host = host, block_device__path = m['device_node'])
            target = mount.target.downcast()
        except ManagedTargetMount.DoesNotExist:
            pass

    if not target:
        target = klass.objects.create(**kwargs)

    _create_mounts(target, mounts)
    return target


def _create_mounts(target, mounts):
    from configure.models import ManagedHost, Lun, LunNode, ManagedTargetMount
    lun = None
    for m in mounts:
        host = ManagedHost.objects.get(address = m['host'])
        try:
            lun_node = LunNode.objects.get(host = host, path = m['device_node'])
            lun = lun_node.lun
            break
        except LunNode.DoesNotExist:
            pass

    if not lun:
        lun = Lun.objects.create(shareable = (len(mounts) > 1))

    for m in mounts:
        host = ManagedHost.objects.get(address = m['host'])
        try:
            lun_node = LunNode.objects.get(host = host, path = m['device_node'])
        except LunNode.DoesNotExist:
            lun_node = LunNode.objects.create(host = host, path = m['device_node'], lun = lun)
        if len(mounts) > 1:
            primary = m['primary']
        else:
            primary = True

        try:
            ManagedTargetMount.objects.get(
                    block_device = lun_node,
                    target = target,
                    host = host,
                    primary = primary)
        except ManagedTargetMount.DoesNotExist:
            ManagedTargetMount.objects.create(
                    block_device = lun_node,
                    target = target,
                    host = host,
                    mount_point = target.default_mount_path(host),
                    primary = primary)


# FIXME: we rely on the good faith of the .json file's author to use
# our canonical names for devices.  We must normalize them to avoid
# the risk of double-using a LUN.
def _load(text):
    from configure.models import ManagedHost, ManagedMgs, ManagedFilesystem
    import json
    data = json.loads(text)

    for host_info in data['hosts']:
        try:
            ManagedHost.objects.get(address = host_info['address'])
        except ManagedHost.DoesNotExist:
            ManagedHost.create_from_string(host_info['address'])

    for mgs_info in data['mgss']:
        mgs = _find_or_create_target(ManagedMgs, mgs_info['mounts'], name = "MGS")

    for filesystem_info in data['filesystems']:
        # We collect up ConfParams for all targets and set them at the end for each filesystem
        from configure.lib.conf_param import all_params
        conf_param_objects = []

        from configure.models import ManagedMdt, MdtConfParam, FilesystemClientConfParam, ManagedOst, OstConfParam

        # Look for the MGS that the user specified by hostname
        fs_mgs_host = ManagedHost.objects.get(address = filesystem_info['mgs'])
        mgs = ManagedMgs.objects.get(managedtargetmount__host = fs_mgs_host)
        filesystem, created = ManagedFilesystem.objects.get_or_create(
                name = filesystem_info['name'], mgs = mgs)

        fs_conf_params = {}
        if 'conf_params' in filesystem_info:
            fs_conf_params = filesystem_info['conf_params']
            _validate_conf_params(fs_conf_params)
        for k, v in fs_conf_params.items():
            try:
                klass, ignore, ignore = all_params[k]
            except:
                # If we don't know anything about this param, then
                # fall back to ClientConfParam (i.e. set it for the
                # filesystem but don't re-set it when targets change)
                klass = FilesystemClientConfParam
            conf_param_objects.append(klass(filesystem = filesystem, key = k, value = v))

        mdt_info = filesystem_info['mdt']
        mdt = _find_or_create_target(ManagedMdt, mdt_info['mounts'], filesystem = filesystem)

        mdt_conf_params = {}
        if 'conf_params' in mdt_info:
            mdt_conf_params = mdt_info['conf_params']
            _validate_conf_params(mdt_conf_params)
        for k, v in mdt_conf_params.items():
            conf_param_objects.append(MdtConfParam(mdt = mdt, key = k, value = v))

        for ost_info in filesystem_info['osts']:
            ost = _find_or_create_target(ManagedOst, ost_info['mounts'], filesystem = filesystem)

            ost_conf_params = {}
            if 'conf_params' in ost_info:
                ost_conf_params = ost_info['conf_params']
                _validate_conf_params(ost_conf_params)
                for k, v in ost_conf_params.items():
                    conf_param_objects.append(OstConfParam(ost = ost, key = k, value = v))
        mgs.set_conf_params(conf_param_objects)


@transaction.commit_on_success
def load_string(text):
    _load(text)


@transaction.commit_on_success
def load_file(path):
    text = open(path).read()
    _load(text)
