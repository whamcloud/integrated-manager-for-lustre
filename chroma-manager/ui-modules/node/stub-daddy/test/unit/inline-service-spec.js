'use strict';
var inlineService =  require('../../inline-service').wiretree;
var format = require('util').format;
var _ = require('lodash-mixins');

describe('inline-service', function () {
  var service, config, registerApiValidator, logger, router, requestValidator, requestStore, mockStatus;
  beforeEach(function () {

    config = {
      status: {
        NOT_FOUND: 404
      },
      methods: {
        GET: 'GET',
        PUT: 'PUT',
        POST: 'POST',
        DELETE: 'DELETE',
        PATCH: 'PATCH'
      },
      requestUrls: {
        MOCK_REQUEST: '/api/mock',
        MOCK_STATE: '/api/mockstate',
        MOCK_LIST: '/api/mocklist'
      }
    };
    registerApiValidator = jasmine.createSpy('registerApiValidator');
    logger = {
      info: jasmine.createSpy('logger.info'),
      debug: jasmine.createSpy('logger.debug'),
      trace: jasmine.createSpy('logger.trace')
    };
    router = jasmine.createSpy('router');
    requestValidator = jasmine.createSpy('requestValidator');
    requestStore = {
      flushEntries: jasmine.createSpy('requestStore.flushEntries')
    };
    mockStatus = {
      flushRequests: jasmine.createSpy('mockStatus.flushRequests')
    };

    service = inlineService(config, registerApiValidator, logger, router, requestValidator,
      requestStore, mockStatus, format, _);
  });

  describe('mock', function () {
    var mock;
    describe('with invalid request', function () {
      beforeEach(function () {
        mock = {
          request: {},
          response: {}
        };

        registerApiValidator.and.returnValue({
          errors: ['error']
        });
      });

      it('should throw error', function () {
        expect(function () { service.mock(mock); }).toThrow();
      });
    });

    describe('with valid request', function () {
      var result;
      beforeEach(function () {
        mock = {
          request: {},
          response: {},
          expires: 1
        };

        registerApiValidator.and.returnValue({errors: []});
        router.and.returnValue({
          status: 201,
          data: {}
        });

        result = service.mock(mock);
      });

      it('should call logger.trace', function () {
        expect(logger.trace).toHaveBeenCalledWith({
          pathname: '/api/mock',
          body: mock
        }, 'Request received');
      });

      it('should call the router', function () {
        expect(router).toHaveBeenCalledWith('/api/mock', {
          url: '/api/mock',
          method: 'POST',
          data: mock,
          headers: {}
        }, mock);
      });

      it('should log that the response was received', function () {
        expect(logger.trace).toHaveBeenCalledWith({
          data: {},
          status: 201
        }, 'Response received.');
      });

      it('should return the data, headers and status', function () {
        expect(result).toEqual({
          data: {},
          status: 201
        });
      });
    });
  });
});
