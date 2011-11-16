#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# Test utility for testing the REST GET and POST calls using 
# command line arguments.
from django.core.management import setup_environ
import optparse
import sys
#import datetime
import settings
setup_environ(settings)

from jsonutils import make_json_call
def main(args):
    option_parser = optparse.OptionParser(
        '%prog [OPTIONS]\nRetrieves chart data of Lustre volumes for a filesystem_id  from Hydra server .\nExample: testgraphapi.py --filesystem_id 1 --starttime 5')
    option_parser.add_option('-s', '--server-url',
                             default='http://clo-centos6-x64-vm2',
                             help='Specify the web service base URL (defaults to http://clo-centos6-x64-vm2.clogeny.com:8000/',
                             dest='url',
                             action='store',
                             )
    option_parser.add_option('--filesystem_id', dest='fs_id',
                             help="Name of the host whose chart data is to be retrived")
    option_parser.add_option('--starttime', dest='start_time',
                             help="Past number of minutes for which data to be fetched")

    options, args = option_parser.parse_args()

    if options.fs_id == None or options.start_time == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')
    
    print  'Unit Test 1: All File system Usage Bar/Column graph:'
    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id='',
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             targetkind='OST',
                             fetchmetrics="kbytestotal kbytesfree filestotal filesfree",   
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 2: File system Usage Bar/Column graph:' 
    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             targetkind='MDT',
                             fetchmetrics="kbytestotal kbytesfree filestotal filesfree",
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 3: File system Read vs Write Chart data for all ManagedOst:'
    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             targetkind='OST',
                             fetchmetrics="stats_read_bytes stats_write_bytes",
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 4: File system MD OP/s :'
    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             targetkind='MDT',
                             fetchmetrics="stats_close stats_getattr stats_getxattr stats_link stats_mkdir stats_mknod stats_open stats_rename stats_rmdir stats_setattr stats_statfs stats_unlink",
                             )
    print 'result:'
    print result
    print '\n\n'


    print'Unit Test 6:  All File system MIOPs Chart data:'
    api_url = base_url + '/api/get_fs_stats_for_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id='',
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             targetkind='MDT',
                             fetchmetrics="stats_close stats_getattr stats_getxattr stats_link stats_mkdir stats_mknod stats_open stats_rename stats_rmdir stats_setattr stats_statfs stats_unlink",
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 8: Server CPU and Memory Charts:'
    api_url = base_url + '/api/get_stats_for_server/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             host_id=1,
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             fetchmetrics="cpu_usage cpu_total mem_MemFree mem_MemTotal",
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 9: ObjectStoreTarget Read Vs Writes:'
    from configure.models import (ManagedFilesystem,
                                  ManagedOst)
    if options.fs_id:
        filesystem = ManagedFilesystem.objects.get(id=options.fs_id)
    else:
        filesystem = ManagedFilesystem.objects.get(id=1)
    fs_osts = ManagedOst.objects.filter(filesystem=filesystem)
    for ost in fs_osts:
        api_url = base_url + '/api/get_stats_for_targets/'
        print '\napi_url: %s' % api_url
        result = make_json_call(api_url,
                                 target_id=ost.id,
                                 starttime=options.start_time,
                                 endtime='',
                                 datafunction='Average',
                                 targetkind='OST',
                                 fetchmetrics="stats_read_bytes stats_write_bytes",   
                                 )
        print 'result:'
        print result
    print '\n\n'

    print 'Unit Test 10: File system connected clients chart:'
    api_url = base_url + '/api/get_fs_stats_for_client/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             fetchmetrics="num_exports",   
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 11: All File systems Connected clients chart:'
    api_url = base_url + '/api/get_fs_stats_for_client/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id='',
                             starttime=options.start_time,
                             endtime='',
                             datafunction='Average',
                             fetchmetrics="num_exports",
                             )
    print 'result:'
    print result
    print '\n\n'
    

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
