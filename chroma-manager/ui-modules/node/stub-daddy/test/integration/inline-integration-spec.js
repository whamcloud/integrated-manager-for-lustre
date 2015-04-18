'use strict';

var wireTreeModule = require('../../index');
var fixtures = require('../fixtures/standard-fixtures');
var format = require('util').format;
var _ = require('lodash-mixins');

describe('inline integration tests', function () {

  var config, service;

  beforeEach(function () {
    var wireTree = wireTreeModule();
    config = wireTree.config;
    service = wireTree.inlineService;
  });

  afterEach(function () {
    service.flush();
  });

  describe('create mock', function () {
    var mock, result;

    ['request', 'response', 'expires', 'dependencies'].forEach(function (valueToRemove) {
      describe(format('%s with required properties missing', valueToRemove), function () {
        beforeEach(function () {
          mock = _.chain({})
            .extend(fixtures.integration.registerSuccessfulMockRequest.json.json)
            .omit(valueToRemove)
            .valueOf();
        });

        it('should fail to create mock', function () {
          expect(service.mock.bind(service, mock)).toThrow();
        });
      });
    });

    describe('with all required properties', function () {
      beforeEach(function () {
        mock = fixtures.integration.registerSuccessfulMockRequest.json.json;
        result = service.mock(mock);
      });

      it('should register the mock successfully', function () {
        expect(result).toEqual({
          data: undefined,
          status: 201,
          headers: {
            'Content-Type': 'application/json'
          }
        });
      });

      describe('and verify mock', function () {
        it('should return matched response', function () {
          var response = service.makeRequest(mock.request);
          expect(response).toEqual(mock.response);
        });
      });
    });
  });

  describe('check mock state', function () {
    var mock, result, response, state;
    beforeEach(function () {
      mock = fixtures.integration.registerSuccessfulMockPOSTRequest.json.json;
      result = service.mock(mock);
      response = service.makeRequest(mock.request);
      state = service.mockState();
    });

    describe('with all registered requests called appropriately', function () {
      it('should be in good state', function () {
        expect(state).toEqual({
          data: [],
          headers: {
            'Content-Type': 'application/json'
          },
          status: 200
        });
      });
    });

    describe('with invalid requests made', function () {
      var extraRequestResponse;
      beforeEach(function () {
        extraRequestResponse = service.makeRequest({
          method: 'POST',
          url: '/invalid/rest/call',
          data: {
            invalid: 'parameter'
          },
          headers: {}
        });
        state = service.mockState();
      });

      it('should indicate an error in the mock state', function () {
        expect(JSON.stringify(state)).toEqual(JSON.stringify({
          data: [
            {
              state: 'ERROR',
              message: 'Call made to non-existent mock',
              data: {
                method: 'POST',
                url: '/invalid/rest/call',
                data: {
                  invalid: 'parameter'
                },
                headers: {}
              }
            }
          ],
          headers: {
            'Content-Type': 'application/json'
          },
          status: 400
        }));
      });
    });
  });

  describe('check mock list', function () {
    var mock, result, registeredMocks, expectedMock;

    beforeEach(function () {
      mock = _({})
        .extend(fixtures.integration.registerSuccessfulMockPOSTRequest.json.json)
        .assign({expires: 1})
        .value();
      result = service.mock(mock);
      registeredMocks = service.registeredMocks();

      expectedMock = function expectedMock (mock, remainingCalls) {
        return {
          data: [
            _.chain({})
              .extend(mock)
              .assign(remainingCalls)
              .valueOf()
          ],
          headers: {
            'Content-Type': 'application/json'
          },
          status: 200
        };
      };
    });

    it('should return all registered mocks', function () {
      expect(JSON.stringify(registeredMocks)).toEqual(
        JSON.stringify(expectedMock(mock, {remainingCalls: 1})));
    });

    describe('after a request to a registered call has been made', function () {
      beforeEach(function () {
        service.makeRequest(mock.request);
        registeredMocks = service.registeredMocks();
      });

      it('should decrement the remainingCalls value after making a request', function () {
        expect(JSON.stringify(registeredMocks)).toEqual(
          JSON.stringify(expectedMock(mock, {remainingCalls: 0})));
      });
    });
  });
});
