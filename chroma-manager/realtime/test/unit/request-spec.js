'use strict';

var requestFactory = require('../../request'),
  sinon = require('sinon');

require('jasmine-sinon');

describe('request', function () {
  var nodeRequest, conf, request, result;

  beforeEach(function () {
    request = {};

    conf = {
      caFile: 'foo'
    };

    nodeRequest = {
      defaults: sinon.stub().returns(request)
    };

    result = requestFactory(conf, nodeRequest);
  });

  it('should create a request with expected defaults', function () {
    expect(nodeRequest.defaults).toHaveBeenCalledWithExactly({
      jar: true,
      json: true,
      ca: conf.caFile,
      strictSSL: false
    });
  });

  it('should return the wrapped request', function () {
    expect(result).toBe(request);
  });
});
