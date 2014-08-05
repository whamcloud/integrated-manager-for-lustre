'use strict';

var requestsModule = require('../../lib/requests').wiretree;
var Promise = require('promise');

describe('request', function () {
  var config, types, requests;

  beforeEach(function () {
    config = {
      registryUrl: 'https://registry.npmjs.org/'
    };

    types = {
      requestThen: jasmine.createSpy('requestThen').and.returnValue(Promise.resolve({
        body: {
          foo: 'bar'
        }
      })),
      requestPipe: jasmine.createSpy('request')
    };

    requests = requestsModule(config, types.requestThen, types.requestPipe);
  });

  ['requestThen', 'requestPipe'].forEach(function (type) {
    describe(type, function () {
      it('should be a function', function () {
        expect(requests[type]).toEqual(jasmine.any(Function));
      });

      it('should call without a proxy', function () {
        requests[type]('foo');

        expect(types[type]).toHaveBeenCalledWith({
          uri: config.registryUrl + 'foo',
          json: true
        });
      });

      it('should call with a proxy', function () {
        config.proxyUrl = 'http://proxy-us.intel.com:911';

        requests = requestsModule(config, types.requestThen, types.requestPipe);

        requests[type]('foo');

        expect(types[type]).toHaveBeenCalledWith({
          uri: config.registryUrl + 'foo',
          json: true,
          proxy: config.proxyUrl
        });
      });
    });
  });

  pit('should parse the response as JSON', function () {
    return requests.requestThen('foo').then(function checkResponse (response) {
      expect(response).toEqual({
        body: {
          foo: 'bar'
        }
      });
    });
  });
});
