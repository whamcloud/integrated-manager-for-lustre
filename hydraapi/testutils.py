
import json
import urllib2


def make_json_call(url, **params):
    """Call one URL, passing JSON-encoded parameters.
    Return the result value.
    """
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
