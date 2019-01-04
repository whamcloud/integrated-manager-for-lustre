# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.models import PowerControlType, PowerControlDevice, PowerControlDeviceOutlet
from chroma_api.authentication import AnonymousAuthentication
from chroma_api.utils import CustomModelResource

from django.forms import ModelForm, ModelChoiceField

from tastypie.authorization import DjangoAuthorization
from tastypie.validation import FormValidation
from tastypie import fields


class ResolvingFormValidation(FormValidation):
    """
    Enhance Tastypie's built-in FormValidation to do resolution of
    incoming resource_uri values to PKs. This seems like it ought to
    be part of Tastypie, oh well.
    """

    def _resolve_uri_to_pk(self, uri):
        from django.core.urlresolvers import resolve

        if not uri:
            return None

        if not isinstance(uri, basestring):
            # Handle lists of URIs
            return [resolve(u)[2]["pk"] for u in uri]
        else:
            # This is the normal case, where we've received a string that
            # looks like "/api/foo/1/", and we need to resolve that into
            # "1".
            return resolve(uri)[2]["pk"]

    def _resolve_relation_uris(self, data):
        # We should be working on a copy of the data, since we're
        # modifying it (FormValidation promises not to modify the bundle).
        data = data.copy()

        fields_to_resolve = [
            k for k, v in self.form_class.base_fields.items() if issubclass(v.__class__, ModelChoiceField)
        ]

        for field in fields_to_resolve:
            if field in data:
                data[field] = self._resolve_uri_to_pk(data[field])

        return data

    # This is pretty much a straight copy of FormValidation's is_valid().
    # It's unfortunate that there's not a cleaner place to hook into the
    # validation processing for subclasses.
    def is_valid(self, bundle, request=None):
        """
        Performs a check on ``bundle.data``to ensure it is valid.

        If the form is valid, an empty list (all valid) will be returned. If
        not, a list of errors will be returned.
        """
        data = bundle.data

        if not bundle.request:
            raise RuntimeError("Must be used with an incoming request")

        # Ensure we get a bound Form, regardless of the state of the bundle.
        if data is None:
            data = {}

        # FormValidation doesn't understand URIs in bundle fields --
        # we need to resolve them into primary keys for the validation
        # to work properly.
        data = self._resolve_relation_uris(data)

        form = self.form_class(data)

        if form.is_valid():
            return {}

        # The data is invalid. Let's collect all the error messages & return
        # them.
        return form.errors


class DeleteablePowerObjectResource(CustomModelResource):
    def obj_delete(self, bundle, **kwargs):
        """
        A ORM-specific implementation of ``obj_delete``.

        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        from tastypie.exceptions import NotFound
        from django.core.exceptions import ObjectDoesNotExist

        obj = kwargs.pop("_obj", None)

        if not hasattr(obj, "delete"):
            try:
                obj = self.obj_get(bundle, **kwargs)
            except ObjectDoesNotExist:
                raise NotFound("A model instance matching the provided arguments could not be found.")

        # Prevent dangling references from Alert objects which will cause
        # 500 errors in the UI.
        obj.mark_deleted()


class PowerControlTypeForm(ModelForm):
    class Meta:
        model = PowerControlType


class PowerControlTypeResource(DeleteablePowerObjectResource):
    """
    A type (make/model, etc.) of power control device
    """

    name = fields.CharField(attribute="display_name", readonly=True)

    def hydrate(self, bundle):
        bundle = super(PowerControlTypeResource, self).hydrate(bundle)

        # We don't want to expose the default credentials via the API, so
        # we've added them to the excluded fields. We do, however, want to
        # allow them to be set, so we have to jam them into the object
        # ourselves.
        for field in ["default_username", "default_password"]:
            if field in bundle.data:
                setattr(bundle.obj, field, bundle.data[field])

        return bundle

    class Meta:
        queryset = PowerControlType.objects.all()
        resource_name = "power_control_type"
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        validation = ResolvingFormValidation(form_class=PowerControlTypeForm)
        ordering = ["name", "make", "model"]
        filtering = {"name": ["exact"], "make": ["exact"]}
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "put", "delete"]
        readonly = ["id"]
        excludes = ["not_deleted", "default_username", "default_password"]
        always_return_data = True


class PowerControlDeviceForm(ModelForm):
    class Meta:
        model = PowerControlDevice

    def _clean_fields(self):
        super(PowerControlDeviceForm, self)._clean_fields()

        # Django, we need to talk. If you tell me I'll have the chance to
        # do custom validation and modify attributes in my model's clean(),
        # then WHY DO YOU DELETE THE VALUE BEFORE I'VE HAD A CHANCE TO FIX IT?!?
        if "address" in self._errors:
            del self._errors["address"]
            field = self.fields["address"]
            self.cleaned_data["address"] = field.widget.value_from_datadict(
                self.data, self.files, self.add_prefix("address")
            )


class PowerControlDeviceResource(DeleteablePowerObjectResource):
    """
    An instance of a power control device, associated with a power control type
    """

    device_type = fields.ToOneField("chroma_api.power_control.PowerControlTypeResource", "device_type", full=True)
    outlets = fields.ToManyField(
        "chroma_api.power_control.PowerControlDeviceOutletResource", "outlets", full=True, null=True
    )

    def hydrate(self, bundle):
        bundle = super(PowerControlDeviceResource, self).hydrate(bundle)

        # We don't want to expose the PDU password via the API, so
        # we've added it to the excluded fields. We do, however, want to
        # allow it to be set, so we have to jam it into the object
        # ourselves.
        if "password" in bundle.data:
            bundle.obj.password = bundle.data["password"]

        return bundle

    class Meta:
        queryset = PowerControlDevice.objects.all()
        resource_name = "power_control_device"
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        validation = ResolvingFormValidation(form_class=PowerControlDeviceForm)
        ordering = ["name"]
        filtering = {"name": ["exact"]}
        excludes = ["not_deleted", "password"]
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "put", "delete"]
        readonly = ["id"]
        always_return_data = True


class PowerControlDeviceOutletForm(ModelForm):
    class Meta:
        model = PowerControlDeviceOutlet


class PowerControlDeviceOutletResource(DeleteablePowerObjectResource):
    """
    An outlet (individual host power control entity) associated with a
    Power Control Device.
    """

    device = fields.ToOneField("chroma_api.power_control.PowerControlDeviceResource", "device")
    host = fields.ToOneField("chroma_api.host.HostResource", "host", null=True)

    class Meta:
        queryset = PowerControlDeviceOutlet.objects.all()
        resource_name = "power_control_device_outlet"
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        validation = ResolvingFormValidation(form_class=PowerControlDeviceOutletForm)
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "put", "delete", "patch"]
        readonly = ["id"]
        excludes = ["not_deleted"]
        always_return_data = True
