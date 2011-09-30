#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# Test utility for testing the REST GET and POST calls using 
# command line arguments.
from django.core.management import setup_environ
import optparse
import sys
import settings
setup_environ(settings)

from jsonutils import make_json_call

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
    option_parser.add_option('--hostname', dest='host_name',  
                             help="Name of the filesystem whose chart data is to be retrieved")
    option_parser.add_option('--targetname', dest='target_name',
                             help="Name of the target (MDT/MGT/OST) whose chart data is to be retrieved")
    option_parser.add_option('--starttime', dest='start_time',
                             help="start time slice for which chart data is to be retrieved")
    option_parser.add_option('--endtime', dest='end_time',
                             help="end time slice for chart data is to be retrieved")
    option_parser.add_option('--interval', dest='time_interval',
                             help="record time collection interval for which chart data is to be retrieved")
    option_parser.add_option('--datafunction', dest='data_function',
                             help="data function could be AVERAGE/MIN/MAX/ALL for which chart data is to be retrieved")

    options, args = option_parser.parse_args()

    if options.filesystem_name == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')
    

    # Unit Test 1 :

    api_url = base_url + '/api/getfsdiskusage/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=options.start_time,
                             endtime=options.end_time,
                             interval=options.time_interval,
                             datafunction=options.data_function,  
                             )
    print '\n result:'
    print result
    print '\n\n'

   # Unit Test 2 :
    api_url = base_url + '/api/getfsinodeusage/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.filesystem_name,
                             starttime=options.start_time,
                             endtime=options.end_time,
                             interval=options.time_interval,
                             datafunction=options.data_function,
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 3  :
    api_url = base_url + '/api/getservercpuusage/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             hostname=options.host_name,
                             starttime=options.start_time,
                             endtime=options.end_time,
                             interval=options.time_interval,
                             datafunction=options.data_function,
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 4 :
    api_url = base_url + '/api/getservermemoryusage/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             hostname=options.host_name,
                             starttime=options.start_time,
                             endtime=options.end_time,
                             interval=options.time_interval,
                             datafunction=options.data_function,
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 5 :
    api_url = base_url + '/api/gettargetreads/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             targetname=options.target_name,
                             starttime=options.start_time,
                             endtime=options.end_time,
                             interval=options.time_interval,
                             datafunction=options.data_function,
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 6 :
    api_url = base_url + '/api/gettargetwrites/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             targetname=options.target_name,
                             starttime=options.start_time,
                             endtime=options.end_time,
                             interval=options.time_interval,
                             datafunction=options.data_function,
                             )
    print '\n result:'
    print result
    print '\n\n'


    return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
