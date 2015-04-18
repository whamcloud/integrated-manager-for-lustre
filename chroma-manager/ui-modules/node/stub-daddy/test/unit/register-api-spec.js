/*jshint node: true*/
'use strict';

var configulator = require('configulator');
var configModule = require('../../config').wiretree;
var modelsModule = require('../../models').wiretree;
var registerAPIModule = require('../../register-api').wiretree;
var url = require('url');
var querystring = require('querystring');

describe('register api module', function () {

  var registerResponse, registerApiValidator, registerAPI, entryRequest, entryResponse, request, body, requestStore,
    config, entryDependencies;
  beforeEach(function() {
    config = configModule(configulator);
    var models = modelsModule(config, url, querystring);
    var logger;

    body = {
      request: {
        method: config.methods.GET,
        url: '/some/path',
        data: {},
        headers: {headerKey: 'header value'}
      },
      response: {
        status: '200',
        data: {dataKey: 'data value'},
        headers: {headerKey: 'header value'}
      },
      dependencies: [
        {
          method: config.methods.PUT,
          url: '/put/path',
          data: {key: 'value'},
          headers: {headerKey: 'header value'}
        }
      ],
      expires: 0
    };
    request = {
      method: config.methods.POST
    };

    entryRequest = new models.Request(
      body.request.method,
      body.request.url,
      body.request.data,
      body.request.headers
    );

    entryResponse = new models.Response(
      body.response.status,
      body.response.headers,
      body.response.data
    );

    entryDependencies = [
      new models.Request(
        body.dependencies[0].method,
        body.dependencies[0].url,
        body.dependencies[0].data,
        body.dependencies[0].headers
      )
    ];

    requestStore = jasmine.createSpyObj('requestStore', ['addEntry']);

    logger = jasmine.createSpyObj('logger', ['info', 'debug', 'trace']);
    registerApiValidator = jasmine.createSpy('registerApiValidator');
    registerAPI = registerAPIModule(requestStore, models, config, registerApiValidator, logger);
  });

  describe('successfully register a mock api with a body in the correct format', function() {
    var json;
    beforeEach(function() {
      json = {
        returnedFromRegisterApiValidator: {
          errors: []
        },
        status: 201
      };

      registerApiValidator.and.returnValue(json.returnedFromRegisterApiValidator);
      registerResponse = registerAPI(request, body);
    });

    it('should call requestStore.addEntry with entryRequest, entryResponse, and body.expires', function() {
      expect(requestStore.addEntry).toHaveBeenCalledWith(entryRequest, entryResponse, body.expires, entryDependencies);
    });

    it('should call registerApiValidator with body', function() {
      expect(registerApiValidator).toHaveBeenCalledWith(body);
    });

    it('should have a status of 201', function() {
      expect(registerResponse.status).toEqual(201);
    });
  });

  describe('failure in registering mock api due to body in invalid format', function() {
    var json;
    beforeEach(function() {
      json = {
        returnedFromRegisterApiValidator: {
          errors: ['some error']
        },
        status: 400
      };

      registerApiValidator.and.returnValue(json.returnedFromRegisterApiValidator);
      registerResponse = registerAPI(request, body);
    });

    it('should not call requestStore.addEntry', function() {
      expect(requestStore.addEntry).not.toHaveBeenCalled();
    });

    it('should call registerApiValidator with body', function() {
      expect(registerApiValidator).toHaveBeenCalledWith(body);
    });

    it('should have a status of 400', function() {
      expect(registerResponse.status).toEqual(400);
    });
  });

  describe('failure due to wrong request method', function() {
    var json;
    beforeEach(function() {
      json = {
        returnedFromRegisterApiValidator: {
          errors: ['another error']
        },
        status: 400
      };
      request.method = config.methods.GET;

      registerApiValidator.and.returnValue(json.returnedFromRegisterApiValidator);
      registerResponse = registerAPI(request, body);
    });

    it('should not call requestStore.addEntry', function() {
      expect(requestStore.addEntry).not.toHaveBeenCalled();
    });

    it('should not call registerApiValidator with body', function() {
      expect(registerApiValidator).not.toHaveBeenCalledWith();
    });

    it('should have a status of 400', function() {
      expect(registerResponse.status).toEqual(400);
    });
  });
});
