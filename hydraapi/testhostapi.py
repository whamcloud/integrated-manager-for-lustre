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
        '%prog [OPTIONS]\nHost resource APIs for Lustre volumes for a filesystem  from Hydra server .\nExample: testhostapi.py --hostname clo-centos6-x64-t1 --operation add/remove')
    option_parser.add_option('-s', '--server-url',
                             default='http://clo-centos6-x64-vm2:8000',
                             help='Specify the web service base URL (defaults to http://clo-centos6-x64-vm2.clogeny.com:8000/',
                             dest='url',
                             action='store',
                             )
    option_parser.add_option('--host', dest='hostname',
                             help="Name of the host to be added/removed to Hydra Server ")
    option_parser.add_option('--operation', dest='operation',
                             help="operation string add or remove ")
    options, args = option_parser.parse_args()

    if options.hostname == None:
        option_parser.print_help()
        exit(-1)
    if options.operation == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')
    if options.operation == 'add':

        # Test 1 :
        api_url = base_url + '/api/addhost/'
        print 'api_url: %s' % api_url
        result = make_json_call(api_url,
                                 hostname=options.hostname,
                                )
        print '\n result:'
        print result
        print '\n\n'
    else:
        # Test 2 :
        api_url = base_url + '/api/removehost/'
        print 'api_url: %s' % api_url
        result = make_json_call(api_url,
                                 hostid=options.hostname,
                                )
        print '\n result:'
        print result
        print '\n\n'
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
