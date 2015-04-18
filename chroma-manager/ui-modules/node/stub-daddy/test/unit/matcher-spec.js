/*jshint node: true*/
'use strict';

var url = require('url');
var querystring = require('querystring');
var configulator = require('configulator');
var requestMatcherModule = require('../../matcher').wiretree;
var configModule =  require('../../config').wiretree;
var modelsModule = require('../../models').wiretree;
var _ = require('lodash-mixins');

describe('test matcher module', function () {

  var requestMatcher, incomingRequest, registeredRequest, config, models;

  beforeEach(function () {
    var data1 = {
      item1: 'item1 value',
      item2: 'item2 value'
    };
    var headers1 = {
      host: 'localhost:8888',
      connection: 'keep-alive',
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko)',
      'content-type': 'text/plain; charset=utf-8',
      accept: '*/*',
      'accept-encoding': 'gzip,deflate,sdch',
      'accept-language': 'en-US,en;q=0.8',
      cookie: 'm=34e2:; csrftoken=Di8V2cFIUliMJVr0tNb8E4SrwCp5QMdg; sessionid=d2fa382c8a220126c1315c94af4bb42c',
      custom: 'my custom header',
      custom2: 'my custom header2'
    };

    config = configModule(configulator);
    models = modelsModule(config, url, querystring);

    incomingRequest = new models.Request(config.methods.GET, '/some/path', data1, headers1);

    var registeredData = {
      item2: 'item2 value'
    };
    var registeredHeaders = {
      custom: 'my custom header'
    };

    spyOn(url, 'parse').and.callThrough();

    registeredRequest = new models.Request(config.methods.GET, '/some/path', registeredData, registeredHeaders);

    requestMatcher = requestMatcherModule(url);
  });

  it('should match with required properties and extra properties in incoming request', function () {
    var result = requestMatcher(incomingRequest, registeredRequest);

    expect(result).toBeTruthy();
  });

  it('should match with required properties and NO extra properties in incoming request', function () {
    incomingRequest.data = _.assign({}, registeredRequest.data);
    incomingRequest.headers = _.assign({}, registeredRequest.headers);

    var result = requestMatcher(incomingRequest, registeredRequest);

    expect(result).toBeTruthy();
  });

  it('should NOT match because one of the required data properties is not in the incoming request', function () {
    registeredRequest.data.extraParam = 'extra param value';

    // In order for this to pass, the incoming request would need to have 'extraParam' on
    // the data property. But it doesn't, so this should fail.
    var result = requestMatcher(incomingRequest, registeredRequest);

    expect(result).toBeFalsy();
  });

  it('should NOT match because one of the required header properties is not in the incoming request', function () {
    registeredRequest.headers.extraParam = 'extra param value';

    // In order for this to pass, the incoming request would need to have 'extraParam' on
    // the headers property. But it doesn't, so this should fail.
    var result = requestMatcher(incomingRequest, registeredRequest);

    expect(result).toBeFalsy();
  });

  it('should NOT match because the method does not match', function () {
    registeredRequest.method = config.methods.POST;

    // The incoming request method is GET so this doesn't match.
    var result = requestMatcher(incomingRequest, registeredRequest);

    expect(result).toBeFalsy();
  });

  it('should NOT match because the url does not match', function () {
    registeredRequest.url = 'bla';

    // The incoming request is /some/path so this doesn't match.
    var result = requestMatcher(incomingRequest, registeredRequest);

    expect(result).toBeFalsy();
  });

  it('should call url.parse', function() {
    expect(url.parse).toHaveBeenCalled();
  });
});
