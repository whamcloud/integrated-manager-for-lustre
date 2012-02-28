
from django.contrib.contenttypes.models import ContentType
from chroma_core.lib.state_manager import StateManager
import chroma_core.lib.conf_param
from tastypie.resources import ModelDeclarativeMetaclass, Resource, ModelResource, ResourceOptions
from tastypie import fields
from tastypie import http


def custom_response(resource, request, response_klass, response_data):
    from tastypie.exceptions import ImmediateHttpResponse
    from tastypie.utils.mime import build_content_type

    desired_format = resource.determine_format(request)
    response = response_klass(content = resource.serialize(request, response_data, desired_format),
            content_type = build_content_type(desired_format))
    return ImmediateHttpResponse(response = response)


def dehydrate_command(command):
    """There are a few places where we invoke CommandResource from other resources
    to build a dict of a Command in 202 responses, so wrap the process here."""
    if command:
        from chroma_api.command import CommandResource
        cr = CommandResource()
        return cr.full_dehydrate(cr.build_bundle(obj = command)).data
    else:
        return None

# monkey-patch ResourceOptions to have a default-empty readonly list
setattr(ResourceOptions, 'readonly', [])


class CustomModelDeclarativeMetaclass(ModelDeclarativeMetaclass):
    """
    Customizations at the metaclass level.
    """
    def __new__(cls, name, bases, attrs):
        new_class = super(CustomModelDeclarativeMetaclass, cls).__new__(cls,
                                                                      name,
                                                                      bases,
                                                                      attrs)
        # At the moment, the only reason for this class' existence is
        # to allow us to define a list of readonly fields in the
        # Resources' Meta classes.  It's kind of a hack, but it works
        # the same way as other resource configuration.  The only
        # wrinkle is that this hacking works best in a metaclass,
        # and there's no way to monkey-patch the __metaclass__ for a
        # class, so we have to either declare this as the __metaclass__
        # for all of our classes which need this functionality or
        # else just have them inherit from a single class which uses
        # this one as its metaclass.  The latter seems cleanest.
        #
        # Why do this instead of setting readonly=True on the various
        # Resource fields?  Because when we explicitly declare a field
        # in a Resource class we lose the ORM-level attributes like
        # help_text.  Plus, in many cases we'd declare fields in the
        # Resources for the sole purpose of marking them readonly,
        # and that adds clutter.
        #
        # TODO: Explore feasibility of getting this readonly fieldlist
        # feature pushed upstream.  Alternatively, fix
        # ModelResource.get_fields() to preserve the underlying
        # ORM field attributes unless they're overridden.

        parent_readonly = []
        # Merge readonly lists from parents into the new class' list.
        try:
            parents = [b for b in bases if issubclass(b, Resource)]
            parents.reverse()

            for p in parents:
                parent_readonly.extend(p._meta.readonly)

        except NameError:
            pass

        # stupid de-dupe tricks
        new_class._meta.readonly = list(set(new_class._meta.readonly +
                                            parent_readonly))
        try:
            for field in new_class._meta.readonly:
                new_class.base_fields[field].readonly = True
        except KeyError:
            pass

        return new_class


class CustomModelResource(ModelResource):
    """
    Container for local customizations to tastypie's ModelResource class.
    """
    __metaclass__ = CustomModelDeclarativeMetaclass


class StatefulModelResource(CustomModelResource):
    content_type_id = fields.IntegerField()
    available_transitions = fields.ListField()
    label = fields.CharField()

    class Meta:
        readonly = ['state', 'content_type_id', 'available_transitions', 'label']

    def dehydrate_available_transitions(self, bundle):
        return StateManager.available_transitions(bundle.obj)

    def dehydrate_content_type_id(self, bundle):
        if hasattr(bundle.obj, 'content_type'):
            return bundle.obj.content_type.pk
        else:
            return ContentType.objects.get_for_model(bundle.obj.__class__).pk

    def dehydrate_label(self, bundle):
        return bundle.obj.get_label()

    # PUT handler for accepting {'state': 'foo', 'dry_run': <true|false>}
    def obj_update(self, bundle, request, **kwargs):
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))

        if hasattr(bundle.obj, 'content_type'):
            stateful_object = bundle.obj.downcast()
        else:
            stateful_object = bundle.obj

        dry_run = bundle.data.get('dry_run', False)
        new_state = bundle.data['state']

        if dry_run:
            # FIXME: should this be a GET to something like /foo/transitions/from/to/
            #        to get information about that transition?
            if stateful_object.state == new_state:
                report = []
            else:
                report = StateManager().get_transition_consequences(stateful_object, new_state)
            raise custom_response(self, request, http.HttpResponse, report)
        else:
            from chroma_core.models import Command
            command = Command.set_state([(stateful_object, new_state)])
            raise custom_response(self, request, http.HttpAccepted,
                    {'command': dehydrate_command(command)})

    def obj_delete(self, request = None, **kwargs):
        obj = self.obj_get(request, **kwargs)
        from chroma_core.models import Command
        command = Command.set_state([(obj, 'removed')])
        raise custom_response(self, request, http.HttpAccepted,
                {'command': dehydrate_command(command)})


class ConfParamResource(StatefulModelResource):
    conf_params = fields.DictField()

    def dehydrate_conf_params(self, bundle):
        try:
            return chroma_core.lib.conf_param.get_conf_params(bundle.obj)
        except NotImplementedError:
            return None

    # PUT handler for accepting {'conf_params': {}}
    def obj_update(self, bundle, request, **kwargs):
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))
        if hasattr(bundle.obj, 'content_type'):
            obj = bundle.obj.downcast()
        else:
            obj = bundle.obj

        if not 'conf_params' in bundle.data:
            super(ConfParamResource, self).obj_update(bundle, request, **kwargs)

        # TODO: validate all the conf_params before trying to set any of them
        try:
            conf_params = bundle.data['conf_params']
            for k, v in conf_params.items():
                chroma_core.lib.conf_param.set_conf_param(obj, k, v)
        except KeyError:
            # TODO: pass in whole objects every time so that I can legitimately
            # validate the presence of this field
            pass

        return bundle
