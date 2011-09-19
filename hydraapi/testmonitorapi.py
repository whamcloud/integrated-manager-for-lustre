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
    # Test 1 : 
    api_url = base_url + '/api/listfilesystems'
    print 'api_url: %s' % api_url
    result  = make_json_call(api_url,
                             )
    print '\n result:'
    print result
    print '\n\n'
    # Test 2 :
    api_url = base_url + '/api/getfilesystem/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.fsname,
                             )
    print '\n result:'
    print result
    print '\n\n'
    # Test 3 :
    api_url = base_url + '/api/getvolumes/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.fsname,
                             )
    print '\n result:'
    print result
    print '\n\n'
    # Test 4 :
    api_url = base_url + '/api/listservers/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                            )
    print '\n result:'
    print result
    print '\n\n'
    # Test 5 :
    api_url = base_url + '/api/getclients/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem=options.fsname,
                             )
    print '\n result:'
    print result
    print '\n\n'
    return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
