# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import sys
import traceback
import logging
import itertools
from chroma_core.models.jobs import SchedulingError
import bisect
from collections import namedtuple


from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.utils import timezone

from tastypie.resources import ModelDeclarativeMetaclass, Resource, ResourceOptions
from tastypie import fields
from tastypie import http
from tastypie.serializers import Serializer
from tastypie.http import HttpBadRequest, HttpMethodNotAllowed
from tastypie.exceptions import ImmediateHttpResponse

from chroma_core.models.command import Command
from chroma_core.models.target import ManagedMgs
from chroma_core.models import StorageResourceRecord, StorageResourceStatistic
from chroma_core.services import log_register
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_api.chroma_model_resource import ChromaModelResource
import chroma_core.lib.conf_param
from chroma_core.models import utils as conversion_util
from iml_common.lib.date_time import IMLDateTime
from chroma_core.lib.metrics import MetricStore, Counter

from collections import defaultdict
from django.db.models.query import QuerySet
from django.db.models import fields as django_fields

log = log_register(__name__)


def custom_response(resource, request, response_klass, response_data):
    from tastypie.exceptions import ImmediateHttpResponse
    from tastypie.utils.mime import build_content_type

    desired_format = resource.determine_format(request)
    response = response_klass(
        content=resource.serialize(request, response_data, desired_format),
        content_type=build_content_type(desired_format),
    )
    return ImmediateHttpResponse(response=response)


def dehydrate_command(command):
    """There are a few places where we invoke CommandResource from other resources
    to build a dict of a Command in 202 responses, so wrap the process here."""
    if command:
        from chroma_api.command import CommandResource

        cr = CommandResource()
        return cr.full_dehydrate(cr.build_bundle(obj=command)).data
    else:
        return None


# Given a dict of queries, turn the variables into the correct format for a django filter.
def filter_fields_to_type(klass, query_dict):
    reserved_fields = ["order_by", "format", "limit", "offset"]

    q = QuerySet(klass)

    query = dict(query_dict)

    fields = {}
    for field in q.model._meta.fields:
        fields[field.column] = field

    # Remove the reserved fields we know about.
    for field in query.keys():
        if field in reserved_fields:
            del query[field]

    # This will error if it find an unknown field and cause the standard tasty pie query to run.
    for field in query.keys():
        try:
            field_type = type(fields[field])
            value = query[field]

            if field_type == django_fields.AutoField or field_type == django_fields.IntegerField:
                value = int(value)
            elif field_type == django_fields.BooleanField:
                value = value.lower() == "true"

            query[field] = value
        except KeyError:
            pass

    return query


# monkey-patch ResourceOptions to have a default-empty readonly list
setattr(ResourceOptions, "readonly", [])


class CustomModelDeclarativeMetaclass(ModelDeclarativeMetaclass):
    """
    Customizations at the metaclass level.
    """

    def __new__(cls, name, bases, attrs):
        new_class = super(CustomModelDeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)
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
        new_class._meta.readonly = list(set(new_class._meta.readonly + parent_readonly))

        for field in new_class._meta.readonly:
            try:
                new_class.base_fields[field].readonly = True
            except KeyError:
                pass

        return new_class


class CustomModelResource(ChromaModelResource):
    """
    Container for local customizations to tastypie's ModelResource class.
    """

    __metaclass__ = CustomModelDeclarativeMetaclass


class StatefulModelResource(CustomModelResource):
    content_type_id = fields.IntegerField()
    available_transitions = fields.ListField()
    available_jobs = fields.ListField()
    label = fields.CharField()
    locks = fields.DictField(help_text="Lists of locked job ids for this object")

    class Meta:
        readonly = [
            "id",
            "immutable_state",
            "state",
            "content_type_id",
            "available_transitions",
            "available_jobs",
            "label",
            "state_modified_at",
            "locks",
        ]

    def dehydrate_content_type_id(self, bundle):
        if hasattr(bundle.obj, "content_type"):
            return bundle.obj.content_type_id
        else:
            return ContentType.objects.get_for_model(bundle.obj.__class__).pk

    def dehydrate_label(self, bundle):
        return bundle.obj.get_label()

    def dehydrate_locks(self, bundle):
        obj = bundle.obj
        obj_key = ContentType.objects.get_for_model(obj.downcast()).natural_key()

        return JobSchedulerClient.get_locks(obj_key, obj.id)

    def alter_detail_data_to_serialize(self, request, bundle):
        """Add post dehydrate data to a single bundle

        Call in methods that call obj_create() and have a flag to create
        a fresh copy of the bundle.

        Recommended to be used in places that call full_dehydrate directly
        around this app to get available_* data added to the bundle.

        Normally as GET call to TastyPie will call the
        alter_list_data_to_serialize hook method which populates the
        available_* data.  In the short circuit case of calling full_dehydrate
        you can use this method to get the available_* post added.

        Example:
          self.alter_detail_data_to_serialize(
            self.full_dehydrate(
                self.build_bundle(obj=the_obj)
                )
            ).data

        or, perhaps more readable

          bundle = self.full_dehydrate(self.build_bundle(obj=the_obj))
          bundle = self.alter_detail_data_to_serialize(bundle)
          data = bundle.data

        """

        to_be_serialized = dict()
        to_be_serialized["objects"] = [bundle]
        to_be_serialized = self.alter_list_data_to_serialize(None, to_be_serialized)

        #  Return the bundle
        return to_be_serialized["objects"][0]

    def alter_list_data_to_serialize(self, request, to_be_serialized):
        """Post process available jobs and state transitions

        This method is a TastyPie hook that is called after all fields
        have been dehydrated.  The available_* methods are no longer
        dehydrated one at a time.  Instead, they are all done in two batched
        calls, and set in the return datastructure here.

        to_be_serialized is a list of TastyPie Bundles composing some
        subclass of StatefulObjects under the key 'objects.

        Returns an updated copy of the input dict.
        """

        batch = []
        for bundle in to_be_serialized["objects"]:
            so_ct_key = ContentType.objects.get_for_model(bundle.obj.downcast()).natural_key()
            batch.append((so_ct_key, bundle.obj.id))

        computed_transitions = JobSchedulerClient.available_transitions(batch)
        computed_jobs = JobSchedulerClient.available_jobs(batch)

        #  decorate the transition lists with verbs
        #  and install in the bundle for return
        for idx, bundle in enumerate(to_be_serialized["objects"]):
            obj_transitions_states_and_verbs = computed_transitions[str(bundle.obj.id)]

            obj_jobs = computed_jobs[str(bundle.obj.id)]

            # TODO: available_transitions is deprecated, use available_actions
            bundle.data["available_transitions"] = obj_transitions_states_and_verbs

            # TODO: available_jobs is deprecated, use available_actions
            bundle.data["available_jobs"] = obj_jobs

            available_actions = sorted(
                obj_transitions_states_and_verbs + obj_jobs, key=lambda action: action["display_order"]
            )
            bundle.data["available_actions"] = available_actions

        return to_be_serialized

    # PUT handler for accepting {'state': 'foo', 'dry_run': <true|false>}
    def obj_update(self, bundle, **kwargs):
        self.is_valid(bundle)

        if bundle.errors:
            raise ImmediateHttpResponse(
                response=self.error_response(bundle.request, bundle.errors[self._meta.resource_name])
            )

        request = bundle.request
        bundle.obj = self.cached_obj_get(bundle, **self.remove_api_resource_names(kwargs))

        stateful_object = bundle.obj

        dry_run = bundle.data.get("dry_run", False)
        if "state" in bundle.data:
            new_state = bundle.data["state"]

            if dry_run:
                # FIXME: should this be a GET to something like /foo/transitions/from/to/
                #        to get information about that transition?
                if stateful_object.state == new_state:
                    report = []
                else:
                    report = JobSchedulerClient.get_transition_consequences(stateful_object, new_state)
                raise custom_response(self, request, http.HttpResponse, report)
            else:
                try:
                    command = Command.set_state([(stateful_object, new_state)])
                except SchedulingError as e:
                    raise custom_response(self, request, http.HttpBadRequest, {"state": e.message})

                if command:
                    raise custom_response(self, request, http.HttpAccepted, {"command": dehydrate_command(command)})
                else:
                    raise custom_response(self, request, http.HttpNoContent, None)
        else:
            return bundle

    def obj_delete(self, bundle, **kwargs):
        obj = self.obj_get(bundle, **kwargs)
        try:
            if obj.immutable_state and "forgotten" in obj.states:
                command = Command.set_state([(obj, "forgotten")])
            else:
                command = Command.set_state([(obj, "removed")])
        except SchedulingError as e:
            raise custom_response(self, bundle.request, http.HttpBadRequest, {"__all__": e.message})
        raise custom_response(self, bundle.request, http.HttpAccepted, {"command": dehydrate_command(command)})


class ConfParamResource(StatefulModelResource):
    conf_params = fields.DictField()

    def dehydrate_conf_params(self, bundle):
        try:
            return chroma_core.lib.conf_param.get_conf_params(bundle.obj)
        except NotImplementedError:
            return None

    # PUT handler for accepting {'conf_params': {}}
    def obj_update(self, bundle, **kwargs):
        self.is_valid(bundle)

        if bundle.errors:
            raise ImmediateHttpResponse(
                response=self.error_response(bundle.request, bundle.errors[self._meta.resource_name])
            )

        request = bundle.request
        bundle.obj = self.cached_obj_get(bundle, **self.remove_api_resource_names(kwargs))
        if hasattr(bundle.obj, "content_type"):
            obj = bundle.obj.downcast()
        else:
            obj = bundle.obj

        # FIXME HYD-1032: PUTing modified conf_params and modified state in the same request will
        # cause one of those two things to be ignored.

        if not "conf_params" in bundle.data or isinstance(obj, ManagedMgs):
            super(ConfParamResource, self).obj_update(bundle, **kwargs)

        try:
            conf_params = bundle.data["conf_params"]
        except KeyError:
            # TODO: pass in whole objects every time so that I can legitimately
            # validate the presence of this field
            pass
        else:
            # Belt-and-braces: child classes should have validated first, but let's
            # make sure (bad conf params can be very harmful)
            errors = chroma_core.lib.conf_param.validate_conf_params(obj.__class__, conf_params)
            if errors:
                raise custom_response(self, request, http.HttpBadRequest, {"conf_params": errors})

            # Store the conf params
            mgs_id = chroma_core.lib.conf_param.set_conf_params(obj, conf_params)

            # If we were returned an MGS, then something has changed, and we will
            # kick off a command to apply the changes to the filesystem
            if mgs_id:
                command_id = JobSchedulerClient.command_run_jobs(
                    [{"class_name": "ApplyConfParams", "args": {"mgs_id": mgs_id}}], "Updating configuration parameters"
                )

                raise custom_response(
                    self,
                    request,
                    http.HttpAccepted,
                    {
                        "command": dehydrate_command(Command.objects.get(pk=command_id)),
                        self.Meta.resource_name: self.alter_detail_data_to_serialize(
                            request, self.full_dehydrate(bundle)
                        ).data,
                    },
                )
            else:
                return super(ConfParamResource, self).obj_update(bundle, **kwargs)

        return bundle


class MetricResource:
    def prepend_urls(self):
        from django.conf.urls.defaults import url

        return [
            url(
                r"^(?P<resource_name>%s)/metric/$" % self._meta.resource_name,
                self.wrap_view("metric_dispatch"),
                name="metric_dispatch",
            ),
            url(
                r"^(?P<resource_name>%s)/(?P<pk>\d+)/metric/$" % self._meta.resource_name,
                self.wrap_view("metric_dispatch"),
                name="metric_dispatch",
            ),
        ]

    def metric_dispatch(self, request, **kwargs):
        """
        GET parameters:
        :metrics: Comma separated list of strings (e.g. kbytesfree,kbytestotal)
        :job: 'id', 'user', or 'name'.
                only supply one metric of 'read_bytes', 'write_bytes', 'read_iops', 'write_iops', 'metadata_iops'
        :begin: Time ISO8601 string, e.g. '2008-09-03T20:56:35.450686Z'
        :end: Time ISO8601 string, e.g. '2008-09-03T20:56:35.450686Z'
        :latest: boolean -- if true, you are asking for a single time point, the latest value
        :max_points: maximum number of datapoints returned, may result in lower resolution samples
        :num_points: return exact number of data points scaled for the date range
        :reduce_fn: one of 'average', 'sum'
        :group_by: an attribute name of the object you're fetching.  For example, to get
                   the total OST stats for a filesystem, when requesting from
                   the target resource, use reduce_fn=sum, group_by=filesystem.
                   If the group_by attribute is absent from a record in the results,
                   that record is discarded.
        """
        errors = defaultdict(list)

        if request.method != "GET":
            return self.create_response(request, "", response_class=HttpMethodNotAllowed)

        latest, update = (request.GET.get(name, "").lower() in ("true", "1") for name in ("latest", "update"))
        if update and latest:
            errors["update"].append("update and latest are mutually exclusive")

        metrics = filter(None, request.GET.get("metrics", "").split(","))
        job = request.GET.get("job", "")
        if job:
            if len(metrics) != 1:
                errors["job"].append("Job metrics must be a single string")
            if latest:
                errors["job"].append("Job metrics and latest are incompatible")

        num_points = 0
        if "num_points" in request.GET:
            try:
                num_points = int(request.GET["num_points"])
            except ValueError:
                errors["num_points"].append("num_points must be a valid integer")
            if latest or update:
                errors["num_points"].append("num_points requires a fixed begin and end")

        begin = end = None
        if not latest:
            try:
                begin = IMLDateTime.parse(request.GET["begin"])
            except KeyError:
                errors["begin"].append("This field is mandatory when latest=false")
            except ValueError:
                errors["begin"].append("Malformed time string")
            try:
                end = IMLDateTime.parse(request.GET["end"])
            except KeyError:
                if update or num_points:
                    errors["end"].append("This field is mandatory when latest=false")
                else:
                    end = timezone.now()
            except ValueError:
                errors["end"].append("Malformed time string")
        if update:
            begin, end = end, timezone.now()

        try:
            max_points = int(request.GET.get("max_points", 1000))
        except ValueError:
            errors["max_points"].append("max_points must be a valid integer")
        if errors:
            return self.create_response(request, errors, response_class=HttpBadRequest)

        if "pk" in kwargs:
            return self.get_metric_detail(request, metrics, begin, end, job, max_points, num_points, **kwargs)
        return self.get_metric_list(request, metrics, begin, end, job, max_points, num_points, **kwargs)

    def _format(self, stats):
        return [{"ts": dt.isoformat(), "data": stats[dt]} for dt in sorted(stats)]

    def _fetch(self, metrics_obj, metrics, begin, end, job, max_points, num_points):
        if job:
            return metrics_obj.fetch_jobs(metrics[0], begin, end, job, max_points, num_points)
        if begin and end:
            return metrics_obj.fetch(metrics, begin, end, max_points, num_points)
        return dict([metrics_obj.fetch_last(metrics)])

    def get_metric_detail(self, request, metrics, begin, end, job, max_points, num_points, **kwargs):
        bundle = self.build_bundle(request=request)
        obj = self.cached_obj_get(bundle, **self.remove_api_resource_names(kwargs))
        metrics = metrics or MetricStore(obj).names
        if isinstance(obj, StorageResourceRecord):
            # FIXME: there is a level of indirection here to go from a StorageResourceRecord to individual time series.
            # Although no longer necessary, time series are still stored in separate resources.
            stats = defaultdict(dict)
            for stat in StorageResourceStatistic.objects.filter(storage_resource=obj, name__in=metrics):
                for dt, data in self._fetch(stat.metrics, metrics, begin, end, job, max_points, num_points).items():
                    stats[dt].update(data)
        else:
            stats = self._fetch(MetricStore(obj), metrics, begin, end, job, max_points, num_points)
        if not job:
            for data in stats.values():
                data.update(dict.fromkeys(set(metrics).difference(data), 0.0))
        return self.create_response(request, self._format(stats))

    def _reduce(self, metrics, results, reduce_fn):
        # Want an overall reduction into one series
        if reduce_fn not in ("sum", "average"):
            raise NotImplementedError
        datetimes = dict((obj_id, sorted(data)) for obj_id, data in results.items())
        result = {}
        for dt in set(itertools.chain(*datetimes.values())):
            result[dt] = counter = Counter.fromkeys(metrics, 0.0)
            for obj_id, stats in results.items():
                data = stats.get(dt, {})
                dts = datetimes[obj_id]
                if dts and not data:  # Didn't have one for this exact timestamp, do we have one before?
                    data = stats[dts[max(bisect.bisect(dts, dt) - 1, 0)]]
                counter.update(data)
            if reduce_fn == "average":
                for name in counter:
                    counter[name] /= len(results)
        return result

    def get_metric_list(self, request, metrics, begin, end, job, max_points, num_points, **kwargs):
        errors = {}
        reduce_fn, group_by = map(request.GET.get, ("reduce_fn", "group_by"))
        if not reduce_fn and group_by:
            errors["reduce_fn"] = "This field is mandatory if 'group_by' is specified"
        if errors:
            return self.create_response(request, errors, response_class=HttpBadRequest)

        try:
            base_bundle = self.build_bundle(request=request)
            objs = self.obj_get_list(bundle=base_bundle, **self.remove_api_resource_names(kwargs))
        except Http404 as exc:
            raise custom_response(self, request, http.HttpNotFound, {"metrics": exc})
        metrics = metrics or set(itertools.chain.from_iterable(MetricStore(obj).names for obj in objs))

        result = dict(
            (obj.id, self._fetch(MetricStore(obj), metrics, begin, end, job, max_points, num_points)) for obj in objs
        )
        if not reduce_fn:
            for obj_id, stats in result.items():
                result[obj_id] = self._format(stats)
            return self.create_response(request, result)
        if not group_by:
            stats = self._reduce(metrics, result, reduce_fn)
            return self.create_response(request, self._format(stats))
        # Want to reduce into groups, one series per group
        groups = defaultdict(dict)
        for obj in objs:
            if hasattr(obj, "content_type"):
                obj = obj.downcast()
            if hasattr(obj, group_by):
                group_val = getattr(obj, group_by)
                groups[getattr(group_val, "id", group_val)][obj.id] = result[obj.id]
        for key in groups:
            stats = self._reduce(metrics, groups[key], reduce_fn)
            groups[key] = self._format(stats)
        return self.create_response(request, groups)


class SeverityResource(ChromaModelResource):
    """Handles serverity for subclasses

    The basis for this Resource is to add the Severity field and support for
    converting it to and from it's FE form (string) and db form (int)
    """

    severity = fields.CharField(
        attribute="severity",
        help_text=("String indicating the severity " "one of %s") % conversion_util.STR_TO_SEVERITY.keys(),
    )

    def dehydrate_severity(self, bundle):
        """Convert from int in DB to String for FE"""

        return logging.getLevelName(bundle.obj.severity)

    def hydrate_severity(self, bundle):
        """Convert severity name to int value for saving to DB"""
        try:
            bundle.data["severity"] = conversion_util.STR_TO_SEVERITY[bundle.data["severity"]]
        except KeyError as exc:
            raise custom_response(
                self, bundle.request, http.HttpBadRequest, {"severity": ["invalid severity: {0}".format(*exc.args)]}
            )
        return bundle

    def build_filters(self, filters=None):
        """FE will send severity strings which are converted to int here"""

        severity = filters.get("severity", None)
        if severity is not None:
            #  Handle single string rep of severity values. (numeric in DB)
            del filters["severity"]
            if severity:
                filters["severity"] = conversion_util.STR_TO_SEVERITY[severity]
        else:
            #  Handle list of string reps of severity values (numeric in DB)
            severity_list = filters.getlist("severity__in", None)
            if severity_list:
                del filters["severity__in"]
                converted_list = []
                for severity_str in severity_list:
                    converted_list.append(str(conversion_util.STR_TO_SEVERITY[severity_str]))
                filters.setlist("severity__in", converted_list)

        return super(SeverityResource, self).build_filters(filters)


class BulkResourceOperation(object):
    def _bulk_operation(self, action, object_name, bundle, request, **kwargs):
        bulk_action_results = []
        errors_exist = False

        def _call_action(bulk_action_results, action, data, request, **kwargs):
            try:
                bulk_action_result = action(self, data, request, **kwargs)
            except Exception as e:
                bulk_action_result = self.BulkActionResult(
                    None, str(e), "\n".join(traceback.format_exception(*(sys.exc_info())))
                )

            bulk_action_results.append(bulk_action_result)
            return bulk_action_result.error != None

        for data in bundle.data.get("objects", [bundle.data]):
            errors_exist |= _call_action(bulk_action_results, action, data, request, **kwargs)

        if "objects" in bundle.data:
            raise custom_response(
                self,
                request,
                http.HttpBadRequest if errors_exist else http.HttpAccepted,
                {
                    "objects": [
                        {
                            object_name: bulk_action_result.object,
                            "error": bulk_action_result.error,
                            "traceback": bulk_action_result.traceback,
                        }
                        for bulk_action_result in bulk_action_results
                    ]
                },
            )

        if errors_exist:
            # Return 400, a failure here could mean many things.
            raise custom_response(
                self,
                request,
                http.HttpBadRequest,
                {"error": bulk_action_results[0].error, "traceback": bulk_action_results[0].traceback},
            )
        else:
            # REMOVE BEFORE LANDING
            # TODO: Horrible special case that I don't want to fix up at this time. When command is returned it is returned command: data
            # but everything else is just data.
            # I'm not going to raise a ticket because it will not make the backlog, but at some point the front and back should remove
            # this anomaly.
            if object_name == "csssommand":
                result = {"command": bulk_action_results[0].object}
            else:
                result = bulk_action_results[0].object

            raise custom_response(
                self, request, http.HttpAccepted if bulk_action_results[0].object else http.HttpNoContent, result
            )

    BulkActionResult = namedtuple("BulkActionResult", ["object", "error", "traceback"])


class DateSerializer(Serializer):
    """
    Serializer to format datetimes in ISO 8601 but with timezone
    offset.
    """

    def format_datetime(self, data):
        if timezone.is_naive(data):
            return super(DateSerializer, self).format_datetime(data)

        return data.isoformat()
