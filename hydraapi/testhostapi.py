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


def make_json_call_by_http_method(http_method, url, **params):
    """Call one URL, passing JSON-encoded parameters.
    Return the result value.
    """
    import urllib2
    import json

    # Build a request for the given URL.
    request = urllib2.Request(url)
    # Declare our desire to receive a JSON response.
    request.add_header('Accept', 'application/json')
    # Add any outgoing parameters to the body of the request.
    if params:
        encoded_params = json.dumps(params)
        request.add_header('Content-Length', str(len(encoded_params)))
        request.add_header('Content-Type', 'application/json')
        request.add_data(encoded_params)
        request.get_method = lambda: http_method
    # Retrieve the data, unpack it, and pull out the "result" value.
    try:
        raw_response = urllib2.urlopen(request).read()
    except urllib2.URLError, e:
            # reraise the original erro
            raise Exception(e)

    faultstring = json.loads(raw_response).get('faultstring')
    if faultstring:
        raise Exception(faultstring)
    result = json.loads(raw_response)
    return result


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
    options, args = option_parser.parse_args()

    if options.hostname == None:
        option_parser.print_help()
        exit(-1)
    base_url = options.url.rstrip('/')
    # Test 1 :
    api_url = base_url + '/api/host/'
    print 'api_url: %s' % api_url
    result = make_json_call_by_http_method('GET', api_url,
                                 host_id=1,
                                )
    print '\n result:'
    print result
    print '\n\n'
    # Test 2 :
    api_url = base_url + '/api/host/'
    print 'api_url: %s' % api_url
    result = make_json_call_by_http_method('GET', api_url,
                                 filesystem_id=1,
                                )
    print '\n result:'
    print result
    print '\n\n'
    # Test 3 :
    api_url = base_url + '/api/host/'
    print 'api_url: %s' % api_url
    result = make_json_call_by_http_method('GET', api_url,
                                )
    print '\n result:'
    print result
    print '\n\n'
    # Test 4 :
    api_url = base_url + '/api/host/'
    print 'api_url: %s' % api_url
    result = make_json_call_by_http_method('POST', api_url,
                                 host_name=options.hostname,
                                )
    print '\n result:'
    print result
    print '\n\n'
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
