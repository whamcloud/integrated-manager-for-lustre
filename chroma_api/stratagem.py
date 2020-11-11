from django.db import models
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from toolz.functoolz import partial, flip, compose

import tastypie.http as http
import re

from tastypie import fields
from tastypie.resources import Resource
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from tastypie.validation import Validation
from chroma_api.validation_utils import validate
from chroma_api.utils import custom_response, dehydrate_command, StatefulModelResource
from chroma_core.models import (
    StratagemConfiguration,
    Command,
    get_fs_id_from_identifier,
)

get_bundle_int_val = compose(partial(flip, int, 10), str)

# Postgres can store numbers up to 8 bytes (+9,223,372,036,854,775,807). These values will ultimately be passed back to the web
# interface, where they will be used by javascript. Therefore, the maximum size of an integer is limited to the
# maximum size allowed by javascript, which is Number.MAX_SAFE_INTEGER (9,007,199,254,740,991).
MAX_SAFE_INTEGER = 9007199254740991


def get_duration_type(duration_key):
    return duration_key.split("_")[0].capitalize()


def get_duration(duration_key, bundle):
    try:
        duration = bundle.data.get(duration_key) and get_bundle_int_val(bundle.data.get(duration_key))
    except ValueError:
        return {
            "code": "invalid_argument",
            "message": "{} duration must be an integer value.".format(get_duration_type(duration_key)),
        }

    return duration


def check_duration(duration_key, bundle):
    duration = get_duration(duration_key, bundle)

    if duration is None or isinstance(duration, dict):
        return duration

    if duration > MAX_SAFE_INTEGER:
        return {
            "code": "{}_too_big".format(duration_key),
            "message": "{} duration cannot be larger than {}.".format(
                get_duration_type(duration_key), MAX_SAFE_INTEGER
            ),
        }

    if duration < 0:
        return {
            "code": "{}_too_small".format(duration_key),
            "message": "{} duration cannot be negative.".format(get_duration_type(duration_key)),
        }

    return duration


def validate_duration(bundle):
    purge_duration = check_duration("purge_duration", bundle)

    if isinstance(purge_duration, dict):
        return purge_duration

    report_duration = check_duration("report_duration", bundle)

    if isinstance(report_duration, dict):
        return report_duration

    if purge_duration is not None and report_duration is not None and report_duration >= purge_duration:
        return {"code": "duration_order_error", "message": "Report duration must be less than Purge duration."}


def get_fs_id(bundle):
    if "filesystem" not in bundle.data:
        return ({"code": "filesystem_required", "message": "Filesystem required."}, None)

    fs_identifier = str(bundle.data.get("filesystem"))
    fs_id = get_fs_id_from_identifier(fs_identifier)

    return (fs_identifier, fs_id)


def validate_filesystem(bundle):
    (fs_identifier, fs_id) = get_fs_id(bundle)
    if isinstance(fs_identifier, dict):
        return fs_identifier

    if fs_id is None:
        return {"code": "filesystem_does_not_exist", "message": "Filesystem {} does not exist.".format(fs_identifier)}


class RunStratagemValidation(Validation):
    def is_valid(self, bundle, request=None):
        return validate_duration(bundle) or validate_filesystem(bundle) or {}


class StratagemConfigurationValidation(RunStratagemValidation):
    def is_valid(self, bundle, request=None):
        required_args = ["filesystem"]

        difference = set(required_args) - set(bundle.data.keys())

        if difference:
            return {
                "code": "required_fields_missing",
                "message": "Required fields are missing: {}".format(", ".join(difference)),
            }

        x = check_duration("interval", bundle)

        if isinstance(x, dict):
            return x

        return super(StratagemConfigurationValidation, self).is_valid(bundle, request)


class StratagemConfigurationResource(StatefulModelResource):
    filesystem = fields.ToOneField("chroma_api.filesystem.FilesystemResource", "filesystem")
    interval = fields.CharField(attribute="interval", null=False)
    report_duration = fields.CharField("report_duration", null=True)
    purge_duration = fields.CharField(attribute="purge_duration", null=True)

    def hydrate_interval(self, val):
        return long(val)

    def hydrate_report_duration(self, val):
        return long(val)

    def hydrate_purge_duration(self, val):
        return long(val)

    def dehydrate_interval(self, bundle):
        x = bundle.data.get("interval")

        if x is None:
            return x

        return long(x)

    def dehydrate_filesystem(self, bundle):
        regex = r".*\/(\d+)\/$"
        fs_uri = bundle.data.get("filesystem")
        matches = re.findall(regex, fs_uri)

        try:
            return matches[0]
        except IndexError:
            raise "Could not locate filesystem id."

    def dehydrate_report_duration(self, bundle):
        x = bundle.data.get("report_duration")

        if x is None:
            return x

        return long(x)

    def dehydrate_purge_duration(self, bundle):
        x = bundle.data.get("purge_duration")

        if x is None:
            return x

        return long(x)

    def get_resource_uri(self, bundle=None, url_name=None):
        return Resource.get_resource_uri(self)

    class Meta:
        resource_name = "stratagem_configuration"
        queryset = StratagemConfiguration.objects.all()
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ["get", "post"]
        detail_allowed_methods = ["get", "put", "delete"]
        validation = StratagemConfigurationValidation()
        filtering = {"filesystem": ["exact"]}

    @validate
    def obj_update(self, bundle, **kwargs):
        command_id = JobSchedulerClient.update_stratagem(bundle.data)

        try:
            command = Command.objects.get(pk=command_id)
        except ObjectDoesNotExist:
            command = None

        raise custom_response(self, bundle.request, http.HttpAccepted, {"command": dehydrate_command(command)})

    @validate
    def obj_create(self, bundle, **kwargs):
        command_id = JobSchedulerClient.configure_stratagem(bundle.data)

        try:
            command = Command.objects.get(pk=command_id)
        except ObjectDoesNotExist:
            command = None

        raise custom_response(self, bundle.request, http.HttpAccepted, {"command": dehydrate_command(command)})
