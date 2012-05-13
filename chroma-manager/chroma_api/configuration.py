#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from collections import defaultdict
from tastypie.authorization import DjangoAuthorization
from tastypie.resources import Resource
from tastypie import fields
from tastypie.validation import Validation
from chroma_api.authentication import AnonymousAuthentication
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.models.host import ManagedHost, VolumeNode
from chroma_core.models.target import ManagedMgs, ManagedMdt, ManagedOst, ManagedTargetMount


class ConfigurationValidation(Validation):
    def is_valid(self, bundle, request = None):
        try:
            mgts = bundle.data['mgts']
        except KeyError:
            return {'mgts': ['This attribute is mandatory']}

        def validate_target(target):
            try:
                mounts = target['mounts']
            except KeyError:
                return ["'mounts' attribute mandatory for targets"]

            errors = []

            def validate_mount(mount):
                try:
                    mount['primary']
                except KeyError:
                    errors.append("'primary' attribute is mandatory for target mounts")
                else:
                    try:
                        host = ManagedHost.objects.get(address = mount['host'])
                    except KeyError:
                        errors.append("'host' attribute is mandatory for target mounts")
                    except ManagedHost.DoesNotExist:
                        errors.append("Host with address '%s' does not exist" % mount['host'])
                    else:
                        try:
                            VolumeNode.objects.get(path = mount['path'], host = host)
                        except KeyError:
                            errors.append("'path' attribute is mandatory for target mounts")
                        except VolumeNode.DoesNotExist:
                            errors.append("Device node '%s' on host '%s' not found" % (mount['path'], host))

                return errors

            for mount_data in mounts:
                validate_mount(mount_data)

            return errors

        def validate_filesystem(fs_data):
            errors = []
            if not 'name' in fs_data:
                errors.append("'name' attribute is mandatory for filesystems")

            def validate_target_list(name):
                try:
                    target_list = fs_data[name]
                except KeyError:
                    errors.append("'%s' attribute is mandatory for filesystems" % name)
                else:
                    for target_data in target_list:
                        errors.extend(validate_target(target_data))

            validate_target_list('mdts')
            validate_target_list('osts')

            return errors

        errors = defaultdict(list)
        for mgt_data in mgts:
            mgt_errors = validate_target(mgt_data)
            if not mgt_errors:
                try:
                    filesystems = mgt_data['filesystems']
                except KeyError:
                    mgt_errors.append("'filesystem' attribute mandatory for MGT")
                else:
                    for fs_data in filesystems:
                        mgt_errors.extend(validate_filesystem(fs_data))
            if mgt_errors:
                errors['mgts'].extend(mgt_errors)

        return errors


class Configuration(object):
    pass


class ConfigurationResource(Resource):
    """
    By default this will give a configuration dump that is suitable
    for re-creating a Chroma server managing the same targets that
    are managed by this Chroma server.

    Pass the 'template=True' as a parameter to a GET in order to receive
    a template suitable for creating a new filesystem on identically named
    hosts/devices.
    """
    mgts = fields.ListField()
    hosts = fields.ListField()

    class Meta:
        resource_name = 'configuration'
        object_class = Configuration
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ['get', 'post']
        get_allowed_methods = []
        validation = ConfigurationValidation()

    def dehydrate_hosts(self, bundle):
        return [{'address': h.address} for h in ManagedHost.objects.all()]

    def _dehydrate_target(self, target):
        data = {'mounts': []}
        for tm in target.managedtargetmount_set.all():
            data['mounts'].append({
                "host": tm.host.address,
                "path": tm.volume_node.path,
                "primary": tm.primary
            })

        if target.state in ['unmounted', 'mounted']:
            data['state'] = target.state
            data['uuid'] = target.uuid
            data['name'] = target.name
            data['inode_size'] = target.inode_size
            data['bytes_per_inode'] = target.bytes_per_inode
            data['inode_count'] = target.inode_count
            data['ha_label'] = target.ha_label
            data['immutable_state'] = target.immutable_state

        return data

    def dehydrate_mgts(self, bundle):
        mgts = []
        for mgt in ManagedMgs.objects.all():
            mgt = self._dehydrate_target(mgt)
            mgt['filesystems'] = []
            for fs in ManagedFilesystem.objects.all():
                filesystem = {}
                filesystem['name'] = fs.name
                filesystem['state'] = fs.state
                filesystem['mdts'] = [self._dehydrate_target(mdt) for mdt in ManagedMdt.objects.filter(filesystem = fs)]
                filesystem['osts'] = [self._dehydrate_target(ost) for ost in ManagedOst.objects.filter(filesystem = fs)]
                filesystem['immutable_state'] = fs.immutable_state
                mgt['filesystems'].append(filesystem)
            mgts.append(mgt)

        return mgts

    def get_list(self, request = None, **kwargs):
        bundle = self.build_bundle(request = request)
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            'resource_name': self._meta.resource_name,
            'api_name': self._meta.api_name
            }

        return self._build_reverse_url('api_dispatch_list', kwargs = kwargs)

    def load_target(self, target, klass, **kwargs):
        def get_node(mount):
            host_address = mount['host']
            path = mount['path']
            host = ManagedHost.objects.get(address = host_address)
            return VolumeNode.objects.get(host = host, path = path)

        volume = None
        for mount in target['mounts']:
            volume_node = get_node(mount)
            if not volume:
                volume = volume_node.volume
            else:
                if volume != volume_node.volume:
                    raise RuntimeError("")

        mounts = target.pop('mounts')
        for k, v in target.items():
            if k != 'mounts' and k != 'filesystems':
                kwargs[k] = v
        kwargs['volume'] = volume

        target = klass.objects.create(**kwargs)
        for mount in mounts:
            volume_node = get_node(mount)
            ManagedTargetMount.objects.create(
                target = target,
                volume_node = volume_node,
                host = volume_node.host,
                mount_point = volume_node.path,
                primary = mount['primary']
            )

        return target

    def obj_create(self, bundle, request = None):
        self.is_valid(bundle, request)
        if bundle.errors:
            self.error_response(bundle.errors, request)

        for mgt in bundle.data['mgts']:
            mgs = self.load_target(mgt, ManagedMgs)
            for fs_data in mgt['filesystems']:
                filesystem = ManagedFilesystem.objects.create(name = fs_data['name'], mgs = mgs)
                for ost_data in fs_data['osts']:
                    self.load_target(ost_data, ManagedOst, filesystem = filesystem)
                for mdt_data in fs_data['mdts']:
                    self.load_target(mdt_data, ManagedMdt, filesystem = filesystem)

        return bundle
