
import datetime
import dateutil.parser
import bisect

from django.contrib.contenttypes.models import ContentType
from chroma_core.lib.state_manager import StateManager
import settings
import chroma_core.lib.conf_param

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie import http
from tastypie.http import HttpBadRequest, HttpMethodNotAllowed
from chroma_core.lib.metrics import R3dMetricStore

from collections import defaultdict


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


class StatefulModelResource(ModelResource):
    content_type_id = fields.IntegerField()
    available_transitions = fields.ListField()
    label = fields.CharField()

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


class MetricResource:
    def override_urls(self):
        from django.conf.urls.defaults import url
        return [
            url(r"^(?P<resource_name>%s)/metric/$" % self._meta.resource_name, self.wrap_view('metric_dispatch'), name="metric_dispatch"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\d+)/metric/$" % self._meta.resource_name, self.wrap_view('metric_dispatch'), name="metric_dispatch"),
        ]

    def metric_dispatch(self, request, **kwargs):
        """
        GET parameters:
        :metrics: Comma separated list of strings (e.g. kbytesfree,kbytestotal)
                  If a datapoint for a particular object does not have ALL of the
                  requested metrics, that datapoint is discarded.
        :begin: Time ISO8601 string, e.g. '2008-09-03T20:56:35.450686Z'
        :end: Time ISO8601 string, e.g. '2008-09-03T20:56:35.450686Z'
        :latest: boolean -- if true, you are asking for a single time point, the latest value
        :update: boolean -- if true, then begin,end specifies the region you've already presented
                 and you're asking for values *since* end.
        :reduce_fn: one of 'average', 'sum'
        :group_by: an attribute name of the object you're fetching.  For example, to get
                   the total OST stats for a filesystem, when requesting from
                   the target resource, use reduce_fn=sum, group_by=filesystem.
                   If the group_by attribute is absent from a record in the results,
                   that record is discarded.
        """
        errors = defaultdict(list)

        if request.method != 'GET':
            return self.create_response(request, "", response_class = HttpMethodNotAllowed)

        latest = request.GET.get('latest', False)
        if latest:
            latest = (latest.lower() == 'true' or latest == '1')

        try:
            metrics = request.GET['metrics'].split(",")
            if len(metrics) == 0:
                errors['metrics'].append("Metrics must be a comma separated list of 1 or more strings")
        except KeyError:
            errors['metrics'].append("This field is mandatory")

        if not latest:
            try:
                begin = dateutil.parser.parse(request.GET['begin'])
            except KeyError:
                errors['begin'].append("This field is mandatory when latest=false")
            except ValueError:
                errors['begin'].append("Malformed time string")

            try:
                end = dateutil.parser.parse(request.GET['end'])
            except KeyError:
                errors['end'].append("This field is mandatory when latest=false")
            except ValueError:
                errors['end'].append("Malformed time string")

        update = request.GET.get('update', False)
        if update:
            update = (update.lower() == 'true' or update == '1')

        if update and latest:
            errors['update'].append("update and latest are mutually exclusive")

        if errors:
            return self.create_response(request, errors, response_class = HttpBadRequest)

        if update:
            begin = end
            end = datetime.datetime.now()
            # TODO: logic for dealing with incomplete values during update
        elif latest:
            begin = end = None

        if 'pk' in kwargs:
            return self.get_metric_detail(request, metrics, begin, end, **kwargs)
        else:
            return self.get_metric_list(request, metrics, begin, end, **kwargs)

    def _format_timestamp(self, ts):
        return datetime.datetime.fromtimestamp(ts).isoformat() + "Z"

    def _fetch(self, metrics_obj, metrics, begin, end):
        if begin and end:
            return metrics_obj.fetch("Average", fetch_metrics = metrics, start_time = begin, end_time = end)
        else:
            return (metrics_obj.fetch_last(fetch_metrics = metrics),)

    def get_metric_detail(self, request, metrics, begin, end, **kwargs):
        obj = self.cached_obj_get(request=request, **self.remove_api_resource_names(kwargs))
        from chroma_core.models import StorageResourceRecord, StorageResourceStatistic
        from collections import defaultdict
        result = []
        if isinstance(obj, StorageResourceRecord):
            # FIXME: there is a level of indirection here to go from a StorageResourceRecord
            # to individual time series.  This is needed because although r3d lets you associate
            # multiple variables with one object, it then requires that they call arrive at the same
            # time with the same resolution.  There is no way for chroma to know what resolution
            # the third party statistics will arrive at, and no way to guarantee they are all
            # queried at the same moment, so we have to give r3d an object per time series.
            stats = StorageResourceStatistic.objects.filter(storage_resource = obj, name__in = metrics)
            ts_data = defaultdict(list)
            for stat in stats:
                data = self._fetch(stat.metrics, metrics, begin, end)
                for dp in data:
                    ts_data[dp[0]].append(dp[1])

            for ts in sorted(ts_data.keys()):
                data_list = ts_data[ts]
                data = {}
                for dl in data_list:
                    data.update(dl)
                timestamp = datetime.datetime.fromtimestamp(ts).isoformat() + "Z"
                if None in data.values():
                    continue
                result.append({'ts': timestamp, 'data': data})

        else:
            stats = self._fetch(R3dMetricStore(obj, settings.AUDIT_PERIOD), metrics, begin, end)

            for datapoint in stats:
                # Assume the database was storing UTC
                timestamp = datetime.datetime.fromtimestamp(datapoint[0]).isoformat() + "Z"
                data = datapoint[1]
                if not data:
                    continue
                if None in data.values():
                    continue
                result.append({'ts': timestamp, 'data': data})

        return self.create_response(request, result)

    def _reduce(self, metrics, results, reduce_fn):
        # Want an overall reduction into one series
        all_timestamps = set()
        series_timestamps = {}
        series_datapoints = {}
        for obj_id, datapoints in results.items():
            series_timestamps[obj_id] = []
            series_datapoints[obj_id] = {}
            for datapoint in datapoints:
                series_timestamps[obj_id].append(datapoint['ts'])
                series_datapoints[obj_id][datapoint['ts']] = datapoint['data']
                all_timestamps.add(datapoint['ts'])
        all_timestamps = list(all_timestamps)
        all_timestamps.sort()

        reduced_result = []
        for timestamp in all_timestamps:
            values = []
            for obj_id, datapoints in results.items():
                if not series_datapoints[obj_id]:
                    # Empty series, can't possibly be any
                    continue

                val = series_datapoints[obj_id].get(timestamp, None)
                if not val:
                    # Didn't have one for this exact timestamp, do we have one before?
                    timestamps = series_timestamps[obj_id]
                    i = bisect.bisect(timestamps, timestamp)
                    if i == 0:
                        # Nothing before this, fall back to taking value after this
                        next_value = series_datapoints[obj_id][series_timestamps[obj_id][0]]
                        val = next_value
                    else:
                        prev_timestamp = timestamps[i - 1]
                        last_value = series_datapoints[obj_id][prev_timestamp]
                        val = last_value

                values.append(val)

            if not values:
                continue

            if reduce_fn == 'sum':
                accum = dict([(m, 0) for m in metrics])
                for value in values:
                    for m, v in value.items():
                        accum[m] += v
                reduced_result.append({'ts': self._format_timestamp(timestamp), 'data': accum})
            elif reduce_fn == 'average':
                accum = dict([(m, 0) for m in metrics])
                for value in values:
                    for m, v in value.items():
                        accum[m] += v
                means = dict([(k, v / len(values)) for (k, v) in accum.items()])
                reduced_result.append({'ts': self._format_timestamp(timestamp), 'data': means})
            else:
                raise NotImplementedError

        return reduced_result

    def get_metric_list(self, request, metrics, begin, end, **kwargs):
        errors = {}

        reduce_fn = request.GET.get('reduce_fn', None)
        group_by = request.GET.get('group_by', None)
        if not reduce_fn and group_by:
            errors['reduce_fn'] = "This field is mandatory if 'group_by' is specified"

        if errors:
            return self.create_response(request, errors, response_class = HttpBadRequest)

        objs = self.obj_get_list(request=request, **self.remove_api_resource_names(kwargs))

        result = {}
        for obj in objs:
            stats = self._fetch(R3dMetricStore(obj, settings.AUDIT_PERIOD), metrics, begin, end)
            result[obj.id] = []
            # Assume these come out in chronological order
            for datapoint in stats:
                # Assume the database was storing UTC
                timestamp = datapoint[0]
                data = datapoint[1]

                ENFORCE_NULLNESS = False
                if ENFORCE_NULLNESS:
                    if len(data) != len(metrics):
                        # Discard, we didn't get all our metrics
                        continue

                    if None in data.values():
                        # Discard, incomplete sample
                        continue

                else:
                    # FIXME
                    # This branch is necessary because stats which are really zero are sometimes
                    # populated as None (the ones that Lustre doesn't report until they're nonzero)
                    # -- None is overloaded to either mean "no data at this timestamp" or "lustre
                    # didn't report the stat because it's zero"
                    non_none = False
                    for k, v in data.items():
                        if v == None:
                            data[k] = 0.0
                        else:
                            non_none = True
                    if not non_none:
                        continue
                result[obj.id].append({'ts': timestamp, 'data': data})

        if reduce_fn and not group_by:
            reduced_result = self._reduce(metrics, result, reduce_fn)
            return self.create_response(request, reduced_result)
        elif reduce_fn and group_by:
            # Want to reduce into groups, one series per group
            bins = {}
            for obj in objs:
                if hasattr(obj, 'content_type'):
                    obj = obj.downcast()

                if hasattr(obj, group_by):
                    group_val = getattr(obj, group_by)
                    if not group_val in bins:
                        bins[group_val] = {}
                    bins[group_val][obj.id] = result[obj.id]

            grouped_result = {}
            for group_val, results in bins.items():
                if hasattr(group_val, 'id'):
                    group_val = group_val.id
                grouped_result[group_val] = self._reduce(metrics, results, reduce_fn)

            return self.create_response(request, grouped_result)
        else:
            # Return individual series for each object
            for obj_id, datapoints in result.items():
                for datapoint in datapoints:
                    datapoint['ts'] = self._format_timestamp(datapoint['ts'])
            return self.create_response(request, result)
