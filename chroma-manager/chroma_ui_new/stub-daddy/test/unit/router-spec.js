/*jshint node: true*/
'use strict';

var url = require('url');
var querystring = require('querystring');
var configulator = require('configulator');
var configModule = require('../../config').wiretree;
var modelsModule = require('../../models').wiretree;
var routerModule = require('../../router').wiretree;

describe('router module test', function () {
  var config, dynamicRequest, registerApi, mockState, logger, routes, request, models, router;
  beforeEach(function() {
    dynamicRequest = jasmine.createSpy('dynamicRequest');
    registerApi = jasmine.createSpy('registerApi');
    mockState = jasmine.createSpy('mockState');
    logger = jasmine.createSpyObj('logger', ['info', 'debug', 'warn']);
    routes = {
      restRoutes: {
        '/api/mock': registerApi,
        '/api/mockstate': mockState
      }
    };
    config = configModule(configulator);
    models = modelsModule(config, url, querystring);
    router = routerModule(config, dynamicRequest, routes, logger);

    // a blank request
    request = new models.Request('', '', {}, {});
  });

  it('should call register api', function () {
    registerApi.and.returnValue(200);

    var result = router('/api/mock', request, null);
    expect(result).toEqual(200);
  });

  it('should call mock status', function () {
    mockState.and.returnValue(200);

    var result = router('/api/mockstate', request, null);

    expect(result).toEqual(200);
  });

  it('should return 400 if request is empty', function () {

    var result = router('/some/call', null, null);
    var expected = {
      status: 400
    };

    expect(result).toEqual(expected);
  });

  describe('calling dynamic request', function() {
    var result, mockEntry;
    beforeEach(function() {
      mockEntry = new models.RequestEntry(null, null, 0);
      dynamicRequest.and.returnValue(mockEntry);

      result = router('/any/call', request, null);
    });

    it('should set the result to the entry', function () {
      expect(result).toBe(mockEntry);
    });

    it('should call the dynamicRequest with request and null', function() {
      expect(dynamicRequest).toHaveBeenCalledWith(request, null);
    });
  });

  describe('returning 404 if path name is empty', function() {
    var result, result2, expected;
    beforeEach(function() {
      result = router('', request, null);
      result2 = router(null, request, null);

      expected = {
        status: 404
      };
    });

    it('should have the expected result of a 400 status on the first router call', function() {
      expect(result).toEqual(expected);
    });

    it('should have the expected result of a 400 status on the second router call', function() {
      expect(result2).toEqual(expected);
    });
  });
});
