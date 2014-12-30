'use strict';

require('promise-it');

jasmine.getEnv().catchExceptions(false);

var getStubDaddy = require('stub-daddy');
var getClient = require('../lib/client');
var _ = require('lodash');

describe('Stub daddy client integration', function () {
  var stubDaddy, client, pluckBody;

  pbeforeEach(function () {
    pluckBody = _.property('body');

    stubDaddy = getStubDaddy();
    client = getClient(stubDaddy.config, stubDaddy.validator);
    return stubDaddy.webService.startService();
  });

  pafterEach(function () {
    return stubDaddy.webService.stopService();
  });

  pit('should be empty', function () {
    return client.mockState()
      .then(pluckBody)
      .then(expectToEqual([]));
  });

  describe('adding a one-off mock', function () {
    var mock;

    pbeforeEach(function () {
      mock = {
        request: {
          method: 'GET',
          url: '/api/target',
          data: {},
          headers: {}
        },
        response: {
          status: 200,
          data: { foo: 'bar' },
          headers: {}
        },
        expires: 1
      };

      return client.mock(mock);
    });

    pit('should list the mock in the mock state', function () {
      return client.mockState()
        .catch(pluckBody)
        .then(expectToEqual([{
          state: 'ERROR',
          message: 'Call to expected mock not satisfied.',
          data: _.extend({ remainingCalls: 1 }, mock)
        }]));
    });

    pit('should get the response from the mock', function () {
      return client.makeRequest({path: 'api/target'})
        .then(pluckBody)
        .then(expectToEqual(mock.response.data));
    });

    pit('should be empty after being called once', function () {
      return client.makeRequest({path: 'api/target'})
        .then(client.mockState)
        .then(pluckBody)
        .then(expectToEqual([]));
    });
  });
});
