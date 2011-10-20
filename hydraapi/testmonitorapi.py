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
        '%prog [OPTIONS]\nRetrieves List of Lustre volumes for a filesystem  from Hydra server .\nExample: testmonitorapi.py --filesystem punefs')
    option_parser.add_option('-s', '--server-url',
                             default='http://clo-centos6-x64-vm2:8000',
                             help='Specify the web service base URL (defaults to http://clo-centos6-x64-vm2.clogeny.com:8000/',
                             dest='url',
                             action='store',
                             )
    option_parser.add_option('--filesystem', dest='fsname',
                             help="Name of the filesystem whose information is to be retrieved")
    options, args = option_parser.parse_args()

    if options.fsname == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')
    print 'Unit Test 1: Get list of All File systems:' 
    api_url = base_url + '/api/listfilesystems/'
    print 'api_url: %s' % api_url
    result  = make_json_call(api_url,
                             )
    print 'result:'
    print result
    print '\n\n'
    
    print 'Unit Test 2: Get File system:'
    api_url = base_url + '/api/getfilesystem/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.fsname,
                             )
    print 'result:'
    print result
    print '\n\n'
    
    print 'Unit Test 3: Get volumes for a File system:'
    api_url = base_url + '/api/getvolumes/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.fsname,
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 4: Get volumes for All File systems:'
    api_url = base_url + '/api/getvolumes/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem='',
                             )
    print 'result:'
    print result
    print '\n\n'    
    
    print'Unit  Test 5: Get servers/hosts for a File system:'
    api_url = base_url + '/api/listservers/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.fsname
                            )
    print 'result:'
    print result
    print '\n\n'
 
    print 'Unit  Test 6: Get servers/hosts for All File systems'
    api_url = base_url + '/api/listservers/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=''
                            )
    print 'result:'
    print result
    print '\n\n'  
    
    print 'Unit  Test 7: Get Clients for a File systems'
    api_url = base_url + '/api/getclients/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.fsname,
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'nit  Test 8: Get Clients for All File systems'
    api_url = base_url + '/api/getclients/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem='',
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 9: Get usable devices/luns:'
    api_url = base_url + '/api/get_luns/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                                category='usable'
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 10: Get unused devices/luns:'
    api_url = base_url + '/api/get_luns/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                                category='unused'
                             )
    print 'result:'
    print result
    print '\n\n'

    return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

