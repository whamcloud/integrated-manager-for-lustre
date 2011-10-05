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
        '%prog [OPTIONS]\nRetrieves chart data of Lustre volumes for a filesystem  from Hydra server .\nExample: testliveinfo.py  --hostname clo-pune-lon01 --severity  --eventtype  --scrollsize  --scrollid')
    option_parser.add_option('-s', '--server-url',
                             default='http://clo-centos6-x64-vm2:8000',
                             help='Specify the web service base URL (defaults to http://clo-centos6-x64-vm2.clogeny.com:8000/',
                             dest='url',
                             action='store',
                             )
    option_parser.add_option('--hostname', dest='host_name',
                             help="Name of the host for which event alert job information is to be retrived")
    option_parser.add_option('--severity', dest='severity_type',  
                             help="severity for which event alert job information is to be retrieved")
    option_parser.add_option('--eventtype', dest='event_type',
                             help="event type for which event alert job information is to be retrieved")
    option_parser.add_option('--scrollsize', dest='scroll_size',
                             help="define the scroll size or pagging size for returned result")
    option_parser.add_option('--scrollid', dest='scroll_id',
                             help="fetch a specific scroll or page from the returned result")

    options, args = option_parser.parse_args()

    if options.host_name == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')
    
    # Unit Test 7 :
    api_url = base_url + '/api/geteventsbyfilter/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             hostname=options.host_name,
                             severity=options.severity_type,
                             eventtype=options.event_type,
                             scrollsize=options.scroll_size,
                             scrollid=options.scroll_id,
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 10 :
    api_url = base_url + '/api/getlatestevents/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             )
    print '\n result:'
    print result
    print '\n\n'    

    # Unit Test 9 :
    api_url = base_url + '/api/getalerts/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             active='',
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 9 :
    api_url = base_url + '/api/getalerts/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             active='True',
                             )
    print '\n result:'
    print result
    print '\n\n'

    # Unit Test 11 :
    api_url = base_url + '/api/getjobs/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             )
    print '\n result:'
    print result
    print '\n\n'

    return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
