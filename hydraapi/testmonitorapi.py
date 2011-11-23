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
        '%prog [OPTIONS]\nRetrieves List of Lustre volumes for a filesystem_id  from Hydra server .\nExample: testmonitorapi.py --filesystem_id 1')
    option_parser.add_option('-s', '--server-url',
                             default='http://clo-centos6-x64-vm2:8000',
                             help='Specify the web service base URL (defaults to http://clo-centos6-x64-vm2.clogeny.com:8000/',
                             dest='url',
                             action='store',
                             )
    option_parser.add_option('--filesystem_id', dest='fs_id',
                             help="Name of the filesystem_id whose information is to be retrieved")
    options, args = option_parser.parse_args()

    if options.fs_id == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')
    print 'Unit Test 1: Get list of All File systems:'
    api_url = base_url + '/api/listfilesystems/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,)
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 2: Get File system:'
    api_url = base_url + '/api/getfilesystem/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 3: Get targets for a File system:'
    api_url = base_url + '/api/get_fs_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             kinds=['MDT', 'MGT', 'OST'],
                             host_id=None
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 4: Get targets for All File systems:'
    api_url = base_url + '/api/get_fs_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id='',
                             kinds=['MDT', 'MGT', 'OST'],
                             host_id=None
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 5: Get targets for All File systems:'
    api_url = base_url + '/api/get_targets/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem='',
                             kinds=['MDT', 'MGT', 'OST']
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 6: Get mgt targets for All File systems:'
    api_url = base_url + '/api/get_mgts/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 7: Get targets for All File systems:'
    api_url = base_url + '/api/getvolumesdetails/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             )
    print 'result:'
    print result
    print '\n\n'

    print'Unit  Test 8: Get servers/hosts for a File system:'
    api_url = base_url + '/api/listservers/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=options.fs_id,
                             kinds=['MDT', 'MGT', 'OST']
                            )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit  Test 9: Get servers/hosts for All File systems'
    api_url = base_url + '/api/listservers/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                             filesystem_id=''
                            )
    print 'result:'
    print result
    print '\n\n'

#    print 'Unit  Test 10: Get Clients for a File systems'
#    api_url = base_url + '/api/getclients/'
#    print 'api_url: %s' % api_url
#    result = make_json_call(api_url,
#                             filesystem_id=options.fs_id,
#                             )
#    print 'result:'
#    print result
#    print '\n\n'

#    print 'nit  Test 11: Get Clients for All File systems'
#    api_url = base_url + '/api/getclients/'
#    print 'api_url: %s' % api_url
#    result = make_json_call(api_url,
#                             filesystem_id='',
#                             )
#    print 'result:'
#    print result
#    print '\n\n'

    print 'Unit Test 12: Get usable devices/luns:'
    api_url = base_url + '/api/get_luns/'
    print 'api_url: %s' % api_url
    result = make_json_call(api_url,
                                category='usable'
                             )
    print 'result:'
    print result
    print '\n\n'

    print 'Unit Test 13: Get unused devices/luns:'
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
