#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# REST API Conrtoller for Lustre File systems resource monitor name space
from django.core.management import setup_environ

# Hydra server imports
import settings
setup_environ(settings)

from requesthandler import (AnonymousRequestHandler,
                            extract_request_args)
from configure.models import (ManagedFilesystem,
                            ManagedMdt,
                            ManagedOst,
                            ManagedHost)
from django.shortcuts import get_object_or_404


class GetFSTargetStats(AnonymousRequestHandler):
    @extract_request_args('filesystem_id', 'starttime', 'endtime', 'datafunction', 'targetkind', 'fetchmetrics')
    def run(self, request, filesystem_id, starttime, endtime, datafunction, targetkind, fetchmetrics):
        assert targetkind in ['OST', 'MDT', 'HOST']
        interval = ''
        if filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            return self.metrics_fetch(fs, targetkind, fetchmetrics, starttime, endtime, interval)
        else:
            all_fs_stats = []
            for fs in ManagedFilesystem.objects.all():
                all_fs_stats.extend(self.metrics_fetch(fs, targetkind, fetchmetrics, starttime, endtime, interval))
            return all_fs_stats

    def metrics_fetch(self, fs, target_kind, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
        if target_kind == 'OST':
            if start_time:
                start_time = int(start_time)
                start_time = getstartdate(start_time)
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction, ManagedOst, fetch_metrics=fetch_metrics.split(), start_time=start_time)
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction, ManagedOst, start_time=start_time)
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(ManagedOst, fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(ManagedOst)
        elif target_kind == 'MDT':
            if start_time:
                start_time = int(start_time)
                start_time = getstartdate(start_time)
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction, ManagedMdt, fetch_metrics=fetch_metrics.split(), start_time=start_time)
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction, ManagedMdt, start_time=start_time)
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(ManagedMdt, fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(ManagedMdt)
        elif target_kind == 'HOST':
            if start_time:
                start_time = int(start_time)
                start_time = getstartdate(start_time)
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction, ManagedHost, fetch_metrics=fetch_metrics.split(), start_time=start_time)
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction, ManagedHost, start_time=start_time)
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(ManagedHost, fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(ManagedHost)
        chart_stats = []
        if fs_target_stats:
            if start_time:
                for stats_data in fs_target_stats:
                    stats_data[1]['filesystem'] = fs.name
                    stats_data[1]['timestamp'] = long(stats_data[0])
                    chart_stats.append(stats_data[1])
            else:
                fs_target_stats[1]['filesystem'] = fs.name
                fs_target_stats[1]['timestamp'] = long(fs_target_stats[0])
                chart_stats.append(fs_target_stats[1])
        return chart_stats


class GetFSServerStats(AnonymousRequestHandler):
    @extract_request_args('filesystem_id', 'starttime', 'endtime', 'datafunction', 'fetchmetrics')
    def run(self, request, filesystem_id, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        if filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            return self.metrics_fetch(fs, fetchmetrics, starttime, endtime, interval)
        else:
            all_fs_stats = []
            for fs in ManagedFilesystem.objects.all():
                all_fs_stats.extend(self.metrics_fetch(fs, fetchmetrics, starttime, endtime, interval))
            return all_fs_stats

    def metrics_fetch(self, fs, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                host_stats = fs.metrics.fetch(datafunction, ManagedHost, fetch_metrics=fetch_metrics.split(), start_time=start_time)
            else:
                host_stats = fs.metrics.fetch(datafunction, ManagedHost, start_time=start_time)
        else:
            if fetch_metrics:
                host_stats = fs.metrics.fetch_last(ManagedHost, fetch_metrics=fetch_metrics.split())
            else:
                host_stats = fs.metrics.fetch_last(ManagedHost)
        chart_stats = []
        if host_stats:
            if start_time:
                for stats_data in host_stats:
                    stats_data[1]['filesystem'] = fs.name
                    stats_data[1]['timestamp'] = long(stats_data[0])
                    chart_stats.append(stats_data[1])
            else:
                host_stats[1]['filesystem'] = fs.name
                host_stats[1]['timestamp'] = long(host_stats[0])
                chart_stats.append(host_stats[1])
        return chart_stats


class GetFSMGSStats(AnonymousRequestHandler):
    @extract_request_args('filesystem_id', 'starttime', 'endtime', 'datafunction', 'fetchmetrics')
    def run(self, request, filesystem_id, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        if filesystem_id:
            mgs_stats_metric = []
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            mgs = fs.mgs
            mgs_stats_metric.append(self.metrics_fetch(mgs, fetchmetrics, starttime, endtime, interval))
            return mgs_stats_metric
        else:
            all_mgs_stats_metric = []
            for fs in ManagedFilesystem.objects.all():
                mgs = fs.mgs
                all_mgs_stats_metric.extend(self.metrics_fetch(mgs, fetchmetrics, starttime, endtime, interval))
            return all_mgs_stats_metric

    def metrics_fetch(self, mgs, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                mgs_stats = mgs.metrics.fetch(datafunction, fetch_metrics=fetch_metrics.split(), start_time=start_time)
            else:
                mgs_stats = mgs.metrics.fetch(datafunction, start_time=start_time)
        else:
            if fetch_metrics:
                mgs_stats = mgs.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                mgs_stats = mgs.metrics.fetch_last()
        chart_stats = []
        if mgs_stats:
            if start_time:
                for stats_data in mgs_stats:
                    stats_data[1]['host'] = mgs.name
                    stats_data[1]['timestamp'] = long(stats_data[0])
                    chart_stats.append(stats_data[1])
            else:
                mgs_stats[1]['host'] = mgs.name
                mgs_stats[1]['timestamp'] = long(mgs_stats[0])
                chart_stats.append(mgs_stats[1])
        return chart_stats


class GetServerStats(AnonymousRequestHandler):
    @extract_request_args('host_id', 'starttime', 'endtime', 'datafunction', 'fetchmetrics')
    def run(self, request, host_id, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        if host_id:
            host = get_object_or_404(ManagedHost, pk = host_id)
            return self.metrics_fetch(host, fetchmetrics, starttime, endtime, interval)
        else:
            raise Exception("Unable to find host with host_id=%s" % host_id)

    def metrics_fetch(self, host, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction, fetch_metrics=fetch_metrics.split(), start_time=start_time)
            else:
                host_stats = host.metrics.fetch(datafunction, start_time=start_time)
        else:
            if fetch_metrics:
                host_stats = host.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                host_stats = host.metrics.fetch_last()
        chart_stats = []
        if host_stats:
            if start_time:
                for stats_data in host_stats:
                    stats_data[1]['host'] = host.address
                    stats_data[1]['timestamp'] = long(stats_data[0])
                    chart_stats.append(stats_data[1])
            else:
                host_stats[1]['host'] = host.address
                host_stats[1]['timestamp'] = long(host_stats[0])
                chart_stats.append(host_stats[1])
        return chart_stats


class GetTargetStats(AnonymousRequestHandler):
    @extract_request_args('target_id', 'starttime', 'endtime', 'datafunction', 'targetkind', 'fetchmetrics')
    def run(self, request, target_id, starttime, endtime, datafunction, targetkind, fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        interval = ''
        if targetkind == 'OST':
            target = get_object_or_404(ManagedOst, pk = target_id)
            return self.metrics_fetch(target, fetchmetrics, starttime, endtime, interval)
        elif targetkind == 'MDT':
            target = get_object_or_404(ManagedMdt, pk = target_id)
            return self.metrics_fetch(target, fetchmetrics, starttime, endtime, interval)

    def metrics_fetch(self, target, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            #Fix Me: ManagedOst/Mdt.metrics.fetch() still not supporting start_time as datetime.datetime.
            # remove below commented code once support is in place.
            #start_time = getstartdate(start_time)
            if fetch_metrics:
                target_stats = target.metrics.fetch(datafunction, fetch_metrics=fetch_metrics.split(), start_time=start_time)
            else:
                target_stats = target.metrics.fetch(datafunction, start_time=start_time)
        else:
            if fetch_metrics:
                target_stats = target.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                target_stats = target.metrics.fetch_last()
        chart_stats = []
        if target_stats:
            if start_time:
                start_time = int(start_time)
                start_time = getstartdate(start_time)
                for stats_data in target_stats:
                    stats_data[1]['target'] = target.name
                    stats_data[1]['timestamp'] = long(stats_data[0])
                    chart_stats.append(stats_data[1])
            else:
                target_stats[1]['target'] = target.name
                target_stats[1]['timestamp'] = long(target_stats[0])
                chart_stats.append(target_stats[1])
        return chart_stats


class GetFSClientsStats(AnonymousRequestHandler):
    @extract_request_args('filesystem_id', 'starttime', 'endtime', 'datafunction', 'fetchmetrics')
    def run(self, request, filesystem_id, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        client_stats = []
        if filesystem_id:
            fs = get_object_or_404(ManagedFilesystem, pk = filesystem_id)
            return self.metrics_fetch(fs, starttime, endtime, interval)
        else:
            for fs in ManagedFilesystem.objects.all():
                client_stats.extend(self.metrics_fetch(fs, starttime, endtime, interval))
            return client_stats

    def metrics_fetch(self, filesystem, start_time, end_time, interval, datafunction='Average'):
        fetch_metrics = "num_exports"
        client_stats = []
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            client_stats = filesystem.metrics.fetch(datafunction, ManagedOst, fetch_metrics=fetch_metrics.split(), start_time=start_time)
        else:
            try:
                client_stats = filesystem.metrics.fetch_last(ManagedOst, fetch_metrics=fetch_metrics.split())
            except:
                pass
        chart_stats = []
        if client_stats:
            if start_time:
                for stats_data in client_stats:
                    stats_data[1]['filesystem'] = filesystem.name
                    stats_data[1]['timestamp'] = long(stats_data[0])
                    chart_stats.append(stats_data[1])
            else:
                client_stats[1]['filesystem'] = filesystem.name
                client_stats[1]['timestamp'] = long(client_stats[0])
                chart_stats.append(client_stats[1])
        return chart_stats


class GetHeatMapFSStats(AnonymousRequestHandler):
    @extract_request_args('filesystem', 'starttime', 'endtime', 'datafunction', 'targetkind', 'fetchmetrics')
    def run(self, request, filesystem, starttime, endtime, datafunction, targetkind, fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        interval = ''
        if filesystem:
            fs = ManagedFilesystem.objects.get(name=filesystem)
            return self.metrics_fetch(fs, targetkind, fetchmetrics, starttime, endtime, interval)
        else:
            all_fs_stats = []
            for fs in ManagedFilesystem.objects.all():
                all_fs_stats.extend(self.metrics_fetch(fs, targetkind, fetchmetrics, starttime, endtime, interval))
            return all_fs_stats

    def metrics_fetch(self, fs, target_kind, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
        fs_target_stats = []
        if target_kind == 'OST':
            if start_time:
                start_time = int(start_time)
                start_time = getstartdate(start_time)
                if fetch_metrics:
                    for ost in ManagedOst.objects.filter(filesystem=fs):
                        ost_stats = ost.metrics.fetch(datafunction, fetch_metrics=fetch_metrics.split(), start_time=start_time)
                        updated_stats_data = []
                        for stats_data in ost_stats:
                            stats_data[1]['targetname'] = ost.name
                            stats_data[1]['timestamp'] = long(stats_data[0])
                            updated_stats_data.append(stats_data[1])
                        fs_target_stats.extend(updated_stats_data)
                else:
                    for ost in ManagedOst.objects.filter(filesystem=fs):
                        ost_stats = ost.metrics.fetch(datafunction, start_time=start_time)
                        updated_stats_data = []
                        for stats_data in ost_stats:
                            stats_data[1]['targetname'] = ost.name
                            stats_data[1]['timestamp'] = long(stats_data[0])
                            updated_stats_data.append(stats_data[1])
                        fs_target_stats.extend(updated_stats_data)
            else:
                if fetch_metrics:
                    for ost in ManagedOst.objects.filter(filesystem=fs):
                        ost_stats = ost.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
                        updated_stats_data = []
                        for stats_data in ost_stats:
                            stats_data[1]['targetname'] = ost.name
                            stats_data[1]['timestamp'] = long(stats_data[0])
                            updated_stats_data.append(stats_data[1])
                        fs_target_stats.extend(updated_stats_data)
                else:
                    for ost in ManagedOst.objects.filter(filesystem=fs):
                        ost_stats = ost.metrics.fetch_last()
                        updated_stats_data = []
                        for stats_data in ost_stats:
                            stats_data[1]['targetname'] = ost.name
                            stats_data[1]['timestamp'] = long(stats_data[0])
                            updated_stats_data.append(stats_data[1])
                        fs_target_stats.extend(updated_stats_data)
        return fs_target_stats


class GetHeatMapServerStats(AnonymousRequestHandler):
    @extract_request_args('filesystem', 'starttime', 'endtime', 'datafunction', 'fetchmetrics')
    def run(self, request, filesystem, starttime, endtime, datafunction, fetchmetrics):
        interval = ''
        if filesystem:
            host_stats_metric = []
            fs = ManagedFilesystem.objects.get(name=filesystem)
            hosts = fs.get_servers()
            for host in hosts:
                host_stats_metric.extend(self.metrics_fetch(host, fetchmetrics, starttime, endtime, interval))
            return host_stats_metric
        else:
            host_stats_metric = []
            for fs in ManagedFilesystem.objects.all():
                hosts = fs.get_servers()
                for host in hosts:
                    host_stats_metric.extend(self.metrics_fetch(host, fetchmetrics, starttime, endtime, interval))
            return host_stats_metric

    def metrics_fetch(self, host, fetch_metrics, start_time, end_time, interval, datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction, fetch_metrics=fetch_metrics.split(), start_time=start_time)
            else:
                host_stats = host.metrics.fetch(datafunction, start_time=start_time)
        else:
            if fetch_metrics:
                host_stats = host.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                host_stats = host.metrics.fetch_last()
        chart_stats = []
        if host_stats:
            if start_time:
                for stats_data in host_stats:
                    stats_data[1]['host'] = host.address
                    stats_data[1]['timestamp'] = long(stats_data[0])
                    stats_data[1]['color_gred'] = getheatmapcolor(fetch_metrics, stats_data[1])
                    chart_stats.append(stats_data[1])
            else:
                host_stats[1]['host'] = host.address
                host_stats[1]['timestamp'] = long(host_stats[0])
                host_stats[1]['color_gred'] = getheatmapcolor(fetch_metrics, host_stats[1])
                chart_stats.append(host_stats[1])
        return chart_stats


def getheatmapcolor(fetch_metrics, stats):
    percentUsed = 0
    if fetch_metrics == "kbytestotal kbytesfree filestotal filesfree":
        try:
            percentUsed = (stats['kbytesfree'] * 100) / stats['kbytestotal']
        except:
            pass
        return getcolorheat(percentUsed)
    elif fetch_metrics == "stats_read_bytes stats_write_bytes":
        try:
            percentUsed = ((stats['stats_read_bytes'] % 100) + (stats['stats_write_bytes'] % 100)) / 2
        except:
            pass
        return getcolorheat(percentUsed)
    elif fetch_metrics == "cpu_usage cpu_total mem_MemFree mem_MemTotal":
        try:
            percentUsed = (stats['cpu_usage'] * 100) / stats['cpu_total']
        except:
            pass
        return getcolorheat(percentUsed)
    else:
        return ''


def getcolorheat(value):
    if value <= 25:
        return '#00ff00'
    elif value <= 50:
        return '#001f00'
    elif value <= 75:
        return '#ffff00'
    elif value <= 100:
        return '#ff0000'


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
