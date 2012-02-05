#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_api.requesthandler import RequestHandler
from chroma_core.models import (ManagedFilesystem,
                            ManagedMdt,
                            ManagedOst,
                            ManagedHost)
from django.shortcuts import get_object_or_404


class GetFSTargetStats(RequestHandler):
    def post(self, request, filesystem_id, starttime, endtime, datafunction, targetkind, fetchmetrics):
        assert targetkind in ['OST', 'MDT', 'HOST']
        interval = ''
        if filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            return metrics_fetch(fs, 'filesystem', targetkind, fetchmetrics, starttime, endtime, interval)
        else:
            all_fs_stats = []
            for fs in ManagedFilesystem.objects.all():
                all_fs_stats.extend(metrics_fetch(fs, 'filesystem', targetkind, fetchmetrics, starttime, endtime, interval))
            return all_fs_stats


class GetFSServerStats(RequestHandler):
    def post(self, request, filesystem_id, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        if filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            return metrics_fetch(fs, 'filesystem', 'HOST', fetchmetrics, starttime, endtime, interval)
        else:
            all_fs_stats = []
            for fs in ManagedFilesystem.objects.all():
                all_fs_stats.extend(metrics_fetch(fs, 'filesystem', 'HOST', fetchmetrics, starttime, endtime, interval))
            return all_fs_stats


class GetFSMGSStats(RequestHandler):
    def post(self, request, filesystem_id, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        if filesystem_id:
            mgs_stats_metric = []
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            mgs = fs.mgs
            mgs_stats_metric.append(metrics_fetch(mgs, 'host', 'TARGET', fetchmetrics, starttime, endtime, interval))
            return mgs_stats_metric
        else:
            all_mgs_stats_metric = []
            for fs in ManagedFilesystem.objects.all():
                mgs = fs.mgs
                all_mgs_stats_metric.extend(metrics_fetch(mgs, 'host', 'TARGET', fetchmetrics, starttime, endtime, interval))
            return all_mgs_stats_metric


class GetServerStats(RequestHandler):
    def post(self, request, host_id, starttime, endtime, datafunction, fetchmetrics):
        print "request.data = %s" % request.data
        interval = ''
        if host_id:
            host = get_object_or_404(ManagedHost, pk = host_id)
            return metrics_fetch(host, 'host', 'MANAGED_HOST', fetchmetrics, starttime, endtime, interval)
        else:
            raise Exception("Unable to find host with host_id=%s" % host_id)


class GetTargetStats(RequestHandler):
    def post(self, request, target_id, starttime, endtime, datafunction, targetkind, fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        interval = ''
        if targetkind == 'OST':
            target = get_object_or_404(ManagedOst, pk = target_id)
            return metrics_fetch(target, 'target', 'TARGET', fetchmetrics, starttime, endtime, interval)
        elif targetkind == 'MDT':
            target = get_object_or_404(ManagedMdt, pk = target_id)
            return metrics_fetch(target, 'target', 'TARGET', fetchmetrics, starttime, endtime, interval)


class GetFSClientsStats(RequestHandler):
    def post(self, request, filesystem_id, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        client_stats = []
        if filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            return metrics_fetch(fs, 'filesystem', 'OST', 'num_exports', starttime, endtime, interval)
        else:
            for fs in ManagedFilesystem.objects.all():
                client_stats.extend(metrics_fetch(fs, 'filesystem', 'OST', 'num_exports', starttime, endtime, interval))
            return client_stats


class GetHeatMapFSStats(RequestHandler):
    def post(self, request, filesystem, starttime, endtime, datafunction, targetkind, fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        interval = ''
        if filesystem:
            fs = ManagedFilesystem.objects.get(name=filesystem)
            return metrics_fetch(fs, 'targetname', targetkind, fetchmetrics, starttime, endtime, interval)
        else:
            all_fs_stats = []
            for fs in ManagedFilesystem.objects.all():
                all_fs_stats.extend(metrics_fetch(fs, 'targetname', targetkind, fetchmetrics, starttime, endtime, interval))
            return all_fs_stats


def metrics_fetch(target, target_name, target_kind, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
    target_name_value = ''
    kind_map = {"OST": ManagedOst,
                "MDT": ManagedMdt,
                "HOST": ManagedHost}
    if start_time:
        start_time = int(start_time)
        #Fix Me: ManagedOst/Mdt.metrics.fetch() still not supporting start_time as datetime.datetime
        # Remove the if statement once support is enabled.
        if target_kind != 'TARGET':
            start_time = getstartdate(start_time)

    if target_kind in kind_map:
        if start_time:
            if fetch_metrics:
                target_stats = target.metrics.fetch(datafunction, kind_map[target_kind], fetch_metrics=fetch_metrics.split(), start_time=start_time)
            else:
                target_stats = target.metrics.fetch(datafunction, kind_map[target_kind], start_time=start_time)
        else:
            if fetch_metrics:
                target_stats = target.metrics.fetch_last(kind_map[target_kind], fetch_metrics=fetch_metrics.split())
            else:
                target_stats = target.metrics.fetch_last(kind_map[target_kind])
        target_name_value = target.name
    elif target_kind in ('MANAGED_HOST', 'TARGET'):
        if start_time:
            if fetch_metrics:
                target_stats = target.metrics.fetch(datafunction, fetch_metrics=fetch_metrics.split(), start_time=start_time)
            else:
                target_stats = target.metrics.fetch(datafunction, start_time=start_time)
        else:
            if fetch_metrics:
                target_stats = target.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                target_stats = target.metrics.fetch_last()
        if target_kind == 'MANAGED_HOST':
            target_name_value = target.pretty_name()
        else:
            target_name_value = target.name
    chart_stats = []
    if target_stats:
        if start_time:
            for stats_data in target_stats:
                stats_data[1][target_name] = target_name_value
                stats_data[1]['timestamp'] = long(stats_data[0])
                chart_stats.append(stats_data[1])
        else:
            target_stats[1][target_name] = target_name_value
            target_stats[1]['timestamp'] = long(target_stats[0])
            chart_stats.append(target_stats[1])
    return chart_stats


def getstartdate(start_time):
    import datetime
    now = lambda: datetime.datetime.now()
    minutes = datetime.timedelta(minutes=1)
    startdatetime = (now() - minutes * int(start_time)).isoformat()
    return _str2dt(startdatetime)


def _str2dt(in_string):
    """Parse a string and return a datetime object."""
    import dateutil.parser
    return dateutil.parser.parse(in_string)
