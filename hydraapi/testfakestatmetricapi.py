#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# Test utility for testing the REST GET and POST calls using
# command line arguments.
from django.core.management import setup_environ
import optparse
import sys
import datetime
import settings
setup_environ(settings)

from testutils import make_json_call


def main(args):
    option_parser = optparse.OptionParser(
        '%prog [OPTIONS]\nRetrieves chart data of Lustre volumes for a filesystem  from Hydra server .\nExample: testgraphapi.py --filesystem punefs --hostname clo-pune-lon01 --targetname=hulkfs01-MDT0000 --starttime 29-20-2011 09:30:45  --endtime  29-20-2011 09:31:45  --interval NA  --datafunction average')
    option_parser.add_option('-s', '--server-url',
                             default='http://clo-centos6-x64-vm2:8000',
                             help='Specify the web service base URL (defaults to http://clo-centos6-x64-vm2.clogeny.com:8000/',
                             dest='url',
                             action='store',
                             )
    option_parser.add_option('--filesystem', dest='filesystem_name',
                             help="Name of the host whose chart data is to be retrived")
#    option_parser.add_option('--hostid', dest='host_id',
#                             help="Name of the filesystem whose chart data is to be retrieved")
#    option_parser.add_option('--target', dest='target_name',
#                             help="Name of the target (MDT/MGT/OST) whose chart data is to be retrieved")
#    option_parser.add_option('--targetkind', dest='target_kind',
#                             help="one of the (MDT/MGT/OST) whose chart data is to be retrieved")
#    option_parser.add_option('--starttime', dest='start_time',
#                             help="start time slice for which chart data is to be retrieved")
#    option_parser.add_option('--endtime', dest='end_time',
#                             help="end time slice for chart data is to be retrieved")
#    option_parser.add_option('--datafunction', dest='data_function',
#                             help="data function could be AVERAGE/MIN/MAX for which chart data is to be retrieved")
#    option_parser.add_option('--fetchmetrics', dest='fetch_metrics',
#                             help="space separated matric name string for fetch")

    options, args = option_parser.parse_args()

    if options.filesystem_name == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')

    # Fetch data for last 10 minutes
    interval = 600
    # Unit Test 1 File system Free Space Chart data:

    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             targetkind='OST',
                             fetchmetrics="kbytestotal kbytesfree filestotal filesfree",
                             )
    print '\n result:'
    print result
    print '\n\n'

    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             targetkind='MDT',
                             fetchmetrics="kbytestotal kbytesfree filestotal filesfree",
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 2  File system Read vs Write Chart data:

    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             targetkind='OST',
                             fetchmetrics="stats_read_bytes stats_write_bytes",
                             )
    print '\n result:'
    print result
    print '\n\n'

    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             targetkind='MDT',
                             fetchmetrics="stats_read_bytes stats_write_bytes",
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 3  File system IOPs Chart data:

    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             targetkind='OST',
                             fetchmetrics="iops1 iops2 iops3 iops4 iops5",
                             )
    print '\n result:'
    print result
    print '\n\n'

    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             targetkind='MDT',
                             fetchmetrics="iops1 iops2 iops3 iops4 iops5",
                             )
    print '\n result:'
    print result
    print '\n\n'

   # Unit Test 4 File system CPU and Memory Charts:
    api_url = base_url + '/api/get_fs_stats_for_server/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             fetchmetrics="cpu_usage cpu_total mem_MemFree mem_MemTotal",
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 5 Server CPU and Memory Charts  :
    api_url = base_url + '/api/get_stats_for_server/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             hostid=1,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             fetchmetrics="cpu_usage cpu_total mem_MemFree mem_MemTotal",
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 6 Target Read Vs Writes:
    api_url = base_url + '/api/get_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             target='hulkfs01-MDT0000',
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             targetkind='MDT',
                             fetchmetrics="stats_read_bytes stats_write_bytes",
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 5 :
    api_url = base_url + '/api/get_fs_stats_for_client/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             fetchmetrics="kbytesfree kbytestotal filesfree filestotal",
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 5 :
    api_url = base_url + '/api/get_fs_ost_heatmap/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=str(datetime.datetime.now()),
                             endtime=str(datetime.datetime.now() - datetime.timedelta(seconds=interval)),
                             datafunction='Average',
                             fetchmetrics="cpu",
                             )
    print '\n result:'
    print result
    print '\n\n'

    return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
