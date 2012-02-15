
from django.contrib.contenttypes.models import ContentType
from chroma_core.lib.state_manager import StateManager
import chroma_core.lib.conf_param
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie import http

import settings


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
    from chroma_api.command import CommandResource
    cr = CommandResource()
    return cr.full_dehydrate(cr.build_bundle(obj = command)).data


class StatefulModelResource(ModelResource):
    content_type_id = fields.IntegerField()
    available_transitions = fields.ListField()
    label = fields.CharField()

    def dehydrate_available_transitions(self, bundle):
        return StateManager.available_transitions(bundle.obj)

    def dehydrate_content_type_id(self, bundle):
        return ContentType.objects.get_for_model(bundle.obj.__class__).pk

    def dehydrate_label(self, bundle):
        return bundle.obj.get_label()

    # PUT handler for accepting {'state': 'foo', 'dry_run': <true|false>}
    def obj_update(self, bundle, request, **kwargs):
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))
        dry_run = bundle.data.get('dry_run', False)
        new_state = bundle.data['state']

        if dry_run:
            # FIXME: should this be a GET to something like /foo/transitions/from/to/
            #        to get information about that transition?
            report = StateManager().get_transition_consequences(bundle.obj, new_state)
            raise custom_response(self, request, http.HttpResponse, report)
        else:
            from chroma_core.models import Command
            command = Command.set_state(bundle.obj, new_state)
            raise custom_response(self, request, http.HttpAccepted,
                    {'command': dehydrate_command(command)})

    def obj_delete(self, request = None, **kwargs):
        obj = self.obj_get(request, **kwargs)
        from chroma_core.models import Command
        command = Command.set_state(obj, 'removed')
        raise custom_response(self, request, http.HttpAccepted, dehydrate_command(command))


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
        if not 'conf_params' in bundle.data:
            super(ConfParamResource, self).obj_update(bundle, request, **kwargs)

        # TODO: validate all the conf_params before trying to set any of them
        try:
            conf_params = bundle.data['conf_params']
            for k, v in conf_params.items():
                chroma_core.lib.conf_param.set_conf_param(bundle.obj, k, v)
        except KeyError:
            # TODO: pass in whole objects every time so that I can legitimately
            # validate the presence of this field
            pass

        return bundle


class MetricResource:
    def override_urls(self):
        from django.conf.urls.defaults import url
        return [
            url(r"^(?P<resource_name>%s)/metric/$" % self._meta.resource_name, self.wrap_view('get_metric_list'), name="get_metric_list"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\d+)/metric/$" % self._meta.resource_name, self.wrap_view('get_metric_detail'), name="get_metric_detail"),
        ]

    def _format_timestamp(self, ts):
        import datetime
        return datetime.datetime.fromtimestamp(ts).isoformat() + "Z"

    def get_metric_detail(self, request, **kwargs):
        """
        GET parameters:
        :metrics: Comma separated list of strings (e.g. kbytesfree,kbytestotal)
        :begin: Time string, e.g. '2008-09-03T20:56:35.450686Z'
        :end: Time string, e.g. '2008-09-03T20:56:35.450686Z'
        """
        from chroma_core.lib.metrics import R3dMetricStore
        from tastypie.http import HttpBadRequest
        import dateutil.parser
        import datetime
        errors = {}

        try:
            metrics = request.GET['metrics'].split(",")
            if len(metrics) == 0:
                errors['metrics'] = "Metrics must be a comma separated list of 1 or more strings"
        except KeyError:
            errors['metrics'] = "This field is mandatory"

        try:
            begin = dateutil.parser.parse(request.GET['begin'])
        except KeyError:
            errors['begin'] = "This field is mandatory"
        except ValueError:
            errors['begin'] = "Malformed time string"

        try:
            end = dateutil.parser.parse(request.GET['end'])
        except KeyError:
            errors['end'] = "This field is mandatory"
        except ValueError:
            errors['end'] = "Malformed time string"

        if errors:
            return self.create_response(request, errors, response_class = HttpBadRequest)

        obj = self.cached_obj_get(request=request, **self.remove_api_resource_names(kwargs))
        stats = R3dMetricStore(obj, settings.AUDIT_PERIOD).fetch("Average",
                fetch_metrics = metrics, start_time = begin, end_time = end)
        result = []
        for datapoint in stats:
            # Assume the database was storing UTC
            timestamp = datetime.datetime.fromtimestamp(datapoint[0]).isoformat() + "Z"
            data = datapoint[1]
            if not data:
                continue
            if None in data.values():
                continue
            result.append([timestamp, data])

        return self.create_response(request, result)

    def _reduce(self, metrics, results, reduce_fn):
        import bisect
        # Want an overall reduction into one series
        all_timestamps = set()
        series_timestamps = {}
        series_datapoints = {}
        for obj_id, datapoints in results.items():
            series_timestamps[obj_id] = []
            series_datapoints[obj_id] = {}
            for datapoint in datapoints:
                series_timestamps[obj_id].append(datapoint[0])
                series_datapoints[obj_id][datapoint[0]] = datapoint[1]
                all_timestamps.add(datapoint[0])
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
                reduced_result.append((self._format_timestamp(timestamp), accum))
            elif reduce_fn == 'average':
                accum = dict([(m, 0) for m in metrics])
                for value in values:
                    for m, v in value.items():
                        accum[m] += v
                means = dict([(k, v / len(values)) for (k, v) in accum.items()])
                reduced_result.append((self._format_timestamp(timestamp), means))
            else:
                raise NotImplementedError

        return reduced_result

    def get_metric_list(self, request, **kwargs):
        from chroma_core.lib.metrics import R3dMetricStore
        from tastypie.http import HttpBadRequest
        import dateutil.parser
        errors = {}

        try:
            metrics = request.GET['metrics'].split(",")
            if len(metrics) == 0:
                errors['metrics'] = "Metrics must be a comma separated list of 1 or more strings"
        except KeyError:
            errors['metrics'] = "This field is mandatory"

        try:
            begin = dateutil.parser.parse(request.GET['begin'])
        except KeyError:
            errors['begin'] = "This field is mandatory"
        except ValueError:
            errors['begin'] = "Malformed time string"

        try:
            end = dateutil.parser.parse(request.GET['end'])
        except KeyError:
            errors['end'] = "This field is mandatory"
        except ValueError:
            errors['end'] = "Malformed time string"

        reduce_fn = request.GET.get('reduce_fn', None)
        group_by = request.GET.get('group_by', None)
        if not reduce_fn and group_by:
            errors['reduce_fn'] = "This field is mandatory if 'group_by' is specified"

        if errors:
            return self.create_response(request, errors, response_class = HttpBadRequest)

        objs = self.obj_get_list(request=request, **self.remove_api_resource_names(kwargs))

        result = {}
        for obj in objs:
            stats = R3dMetricStore(obj, settings.AUDIT_PERIOD).fetch("Average", fetch_metrics = metrics, start_time = begin, end_time = end)
            result[obj.id] = []
            # Assume these come out in chronological order
            for datapoint in stats:
                # Assume the database was storing UTC
                timestamp = datapoint[0]
                data = datapoint[1]
                if len(data) != len(metrics):
                    # Discard, we didn't get all our metrics
                    continue
                if None in data.values():
                    # Discard, incomplete sample
                    continue

                result[obj.id].append([timestamp, data])

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
                    datapoint[0] = self._format_timestamp(datapoint[0])
            return self.create_response(request, result)
