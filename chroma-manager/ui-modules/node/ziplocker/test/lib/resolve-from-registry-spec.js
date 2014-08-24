'use strict';

var resolveFromRegistryModule = require('../../lib/resolve-from-registry').wiretree;
var semver = require('semver');
var Promise = require('promise');

describe('resolve from registry', function () {
  var resolveFromRegistry, requests, config;

  beforeEach(function () {
    requests = {
      requestThen: jasmine.createSpy('requestThen')
    };

    config = {
      registryUrl: 'https://registry.npmjs.org/'
    };

    resolveFromRegistry = resolveFromRegistryModule(requests, semver, config);
  });

  it('should return a function', function () {
    expect(resolveFromRegistry).toEqual(jasmine.any(Function));
  });

  describe('fetching dependency info', function () {
    var dependency, dependencyValue, promise;

    beforeEach(function () {
      dependency = 'express';
      dependencyValue = '4.0.0';

      requests.requestThen.and.returnValue(Promise.resolve({
        body: {
          versions: {
            '4.0.0': { name: 'express' },
            '4.0.1': {}
          }
        }
      }));

      promise = resolveFromRegistry(dependency, dependencyValue);
    });

    it('should make the request for the dependency info', function () {
      expect(requests.requestThen).toHaveBeenCalledWith(config.registryUrl + dependency);
    });

    pit('should return a response object', function () {
      return promise.then(function assertResponse (responseObject) {
        expect(responseObject).toEqual({
          response: { name: 'express' },
          value: '4.0.0'
        });
      });
    });
  });
});
