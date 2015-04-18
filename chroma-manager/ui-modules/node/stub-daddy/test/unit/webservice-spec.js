/*jshint node: true*/
'use strict';

var url = require('url');
var webserviceModule = require('../../webservice').wiretree;
var configulator = require('configulator');
var configModule = require('../../config').wiretree;
var Promise = require('promise');
var _ = require('lodash-mixins');

describe('webservice module', function () {

  var assignments = {};
  var config = configModule(configulator);
  var methods = [config.methods.POST, config.methods.PUT, config.methods.PATCH];

  beforeEach(function () {
    assignments.methods = methods;
    assignments.body = '{"key": "body"}';

    assignments.config = config;

    assignments.mockState = {
      flushRequests: jasmine.createSpy('flushRequests')
    };

    assignments.requestStore = {
      flushEntries: jasmine.createSpy('flushEntries')
    };

    assignments.router = jasmine.createSpy('router');

    assignments.evaluatedResponse = {
      status: 200,
      data: {},
      headers: { 'Content-Type' : 'application/json' }
    };

    assignments.requestData = {
      url: 'https://localhost:8888/path',
      method: assignments.config.methods.POST,
      on: jasmine.createSpy('on').and.callFake(function handleEvent(event, callback) {
        if (event === 'data') {
          callback(assignments.body);
        } else if (event === 'end') {
          callback();
        }
      })
    };

    assignments.server = {
      on: jasmine.createSpy('on'),
      close: jasmine.createSpy('close')
    };

    assignments.createServerResponse = {
      listen: jasmine.createSpy('listen').and.returnValue(assignments.server)
    };

    assignments.socket = {
      setTimeout: jasmine.createSpy('setTimeout'),
      on: jasmine.createSpy('close'),
      destroy: jasmine.createSpy('destroy')
    };

    assignments.dynamicRequest = jasmine.createSpy('dynamicRequest');

    assignments.boundCreateServer = jasmine.createSpy('boundCreateServer').and
      .returnValue(assignments.createServerResponse);

    assignments.request = {
      createServer: {
        bind: jasmine.createSpy('bind').and.returnValue(assignments.boundCreateServer)
      }
    };

    assignments.fsReadThen = jasmine.createSpy('fsReadThen');

    assignments.fsReadThen.and.callFake(function(filename) {
      if (filename === './key.pem')
        return Promise.resolve('key');
      else if (filename === './cert.pem')
        return Promise.resolve('cert');
    });

    // The router should return the evaluated response.
    assignments.router.and.returnValue(assignments.evaluatedResponse);

    assignments.response = jasmine.createSpyObj('response', ['writeHead', 'write', 'end']);

    assignments.logger = jasmine.createSpyObj('logger', ['info', 'debug', 'warn', 'error', 'fatal', 'trace',
      'logByLevel']);

    initializeModule(assignments);
  });

  afterEach(function() {
    var clone = _.cloneDeep(assignments);
    Object.keys(clone).forEach(function clearAssignments(key) {
      delete assignments[key];
    });
  });

  it('should bound createServer once', function (done) {
    assignments.webservice.startService().then(function setService() {
      expect(assignments.boundCreateServer.calls.count()).toEqual(1);
    }).done(done);
  });

  it('should listen on port 8888', function(done) {
    assignments.config.port = 8888;
    assignments.webservice.startService()
      .then(function setService() {
        expect(assignments.createServerResponse.listen).toHaveBeenCalledWith(8888);
      }).done(done);
  });

  it('should the connection callback to have a callback specified', function(done) {
    assignments.webservice.startService()
      .then(function setService() {
      expect(assignments.server.on.calls.argsFor(0)).toEqual(['connection', jasmine.any(Function)]);
    }).done(done);
  });

  describe('Route a POST, PUT, and PATCH with its body and return the response', function () {
    methods.forEach(function (method) {
      beforeEach(function setTestDataForEachMethod(done) {
        assignments.requestData.method = method;
        assignments.config.port = 8000;
        // Test starting the service on port 8000 by passing the argument --port 8000
        assignments.webservice.startService().then(function serviceStarted() {
          // Call the callback being passed into createServer
          assignments.boundCreateServer.calls.argsFor(0)[0](assignments.requestData, assignments.response);

          // call the handleSocketConnection callback
          assignments.server.on.calls.mostRecent().args[1](assignments.socket);

          assignments.port = 8000;
          assignments.responseWriteHeadValue = assignments.evaluatedResponse.status.toString();
          assignments.responseWriteValue = JSON.stringify(assignments.evaluatedResponse.data);
          assignments.socketCallbackCount = 3;
          assignments.connectionCount = 1;
        }).done(done);
      });

      assertWebServiceState(assignments, true);
    });

    it('should return expected call count for socket.on', function() {
      expect(assignments.socket.on.calls.count()).toEqual(3);
    });
  });

  describe('Route a POST, PUT, and PATCH with its body and return bad request since the evaluated response is' +
    ' empty', function () {

      methods.forEach(function (method) {
        beforeEach(function setTestDataForEachMethod(done) {
          assignments.requestData.method = method;
          assignments.router.and.returnValue(null);
          assignments.config.port = 8888;

          assignments.webservice.startService().then(function serviceStarted() {
            // Call the callback being passed into createServer
            assignments.boundCreateServer.calls.argsFor(0)[0](assignments.requestData, assignments.response);

            // call the handleSocketConnection callback
            assignments.server.on.calls.mostRecent().args[1](assignments.socket);

            assignments.port = 8888;
            assignments.responseWriteHeadValue = '404';
            assignments.responseWriteValue = '404';
            assignments.socketCallbackCount = 3;
            assignments.connectionCount = 1;
          }).done(done);
        });

        assertWebServiceState(assignments, true);
      });

      it('should call socket.on 3 times', function() {
        expect(assignments.socket.on.calls.count()).toEqual(3);
      });
    });

  describe('Route a GET with its query parameters and return the response', function () {

    beforeEach(function setTestDataForEachMethod(done) {
      assignments.requestData.method = assignments.config.methods.GET;
      assignments.body = undefined;
      assignments.webservice.startService().then(function serviceStarted() {
        // Call the callback being passed into createServer
        assignments.boundCreateServer.calls.argsFor(0)[0](assignments.requestData, assignments.response);

        // call the handleSocketConnection callback
        assignments.server.on.calls.mostRecent().args[1](assignments.socket);

        assignments.port = 8888;
        assignments.responseWriteHeadValue = assignments.evaluatedResponse.status.toString();
        assignments.responseWriteValue = JSON.stringify(assignments.evaluatedResponse.data);
        assignments.socketCallbackCount = 1;
        assignments.connectionCount = 1;
      }).done(done);
    });

    assertWebServiceState(assignments, true);
  });

  describe('Route a GET with its query parameters and return a bad status if the response is empty', function () {
    beforeEach(function(done) {
      assignments.requestData.method = assignments.config.methods.GET;
      assignments.router.and.returnValue(null);
      assignments.body = undefined;
      assignments.webservice.startService().then(function serviceStarted() {
        // Call the callback being passed into createServer
        assignments.boundCreateServer.calls.argsFor(0)[0](assignments.requestData, assignments.response);

        // call the handleSocketConnection callback
        assignments.server.on.calls.mostRecent().args[1](assignments.socket);

        assignments.port = 8888;
        assignments.responseWriteHeadValue = '404';
        assignments.responseWriteValue = '404';
        assignments.socketCallbackCount = 1;
        assignments.connectionCount = 1;
      }).done(done);
    });

    assertWebServiceState(assignments, true);
  });

  describe('Start the server and make a connection and then close the socket when the connection terminates',
    function () {

      beforeEach(function(done) {
        assignments.webservice.startService().then(function serviceStarted() {
          // Call the callback being passed into createServer
          assignments.boundCreateServer.calls.argsFor(0)[0](assignments.requestData, assignments.response);

          // call the handleSocketConnection callback
          assignments.server.on.calls.mostRecent().args[1](assignments.socket);

          // Simulate a user disconnecting. This will effectively remove the socket.
          assignments.socket.on.calls.mostRecent().args[1]();

          assignments.port = 8888;
          assignments.responseWriteHeadValue = assignments.evaluatedResponse.status.toString();
          assignments.responseWriteValue = JSON.stringify(assignments.evaluatedResponse.data);
          assignments.socketCallbackCount = 1;
          assignments.connectionCount = 0;
        }).done(done);
      });

      assertWebServiceState(assignments, true);

      it('should pass options into the createServer.bind call', function() {
        expect(assignments.request.createServer.bind).toHaveBeenCalledWith(assignments.request, jasmine.any(Object));
      });
    });

  describe('Start the server, accept a request, then stop the server and have no connections', function () {
    beforeEach(function(done) {
      assignments.webservice.startService().then(function serviceStarted() {
        // Call the callback being passed into createServer
        assignments.boundCreateServer.calls.argsFor(0)[0](assignments.requestData, assignments.response);

        // call the handleSocketConnection callback
        assignments.server.on.calls.mostRecent().args[1](assignments.socket);

        assignments.port = 8888;
        assignments.responseWriteHeadValue = assignments.evaluatedResponse.status.toString();
        assignments.responseWriteValue = JSON.stringify(assignments.evaluatedResponse.data);
        assignments.socketCallbackCount = 1;
        assignments.connectionCount = 1;
      }).done(done);
    });

    assertWebServiceState(assignments, true);

    describe('Stop the webservice and verify the server stops', function() {
      beforeEach(function() {
        assignments.webservice.stopService();
      });

      it('should call server.close with the onStopService callback', function() {
        expect(assignments.server.close).toHaveBeenCalledWith(jasmine.any(Function));
      });

      it('should call socket.destroy', function() {
        expect(assignments.socket.destroy).toHaveBeenCalled();
      });

      it('should have an empty connection count', function() {
        expect(assignments.webservice.getConnectionCount()).toEqual(0);
      });
    });
  });

  describe('run the service as http and get the same results as https', function() {
    beforeEach(function(done) {
      config.requestProtocol = 'http';
      assignments.request = {
        createServer: jasmine.createSpy('createServer').and.returnValue(assignments.createServerResponse)
      };
      initializeModule(assignments);

      assignments.webservice.startService().then(function serviceStarted() {
        // Call the callback being passed into createServer
        assignments.request.createServer.calls.argsFor(0)[0](assignments.requestData, assignments.response);

        // call the handleSocketConnection callback
        assignments.server.on.calls.mostRecent().args[1](assignments.socket);

        // Simulate a user disconnecting. This will effectively remove the socket.
        assignments.socket.on.calls.mostRecent().args[1]();

        assignments.port = 8888;
        assignments.responseWriteHeadValue = assignments.evaluatedResponse.status.toString();
        assignments.responseWriteValue = JSON.stringify(assignments.evaluatedResponse.data);
        assignments.socketCallbackCount = 1;
        assignments.connectionCount = 0;
      }).done(done);
    });

    assertWebServiceState(assignments, false);
  });

  /**
   * Executes common assertion statements that are used in the majority of the tests.
   * @param {Object} assignments
   */
  function assertWebServiceState(assignments, https) {
    it('should call router with /path, assignments.request, and the body in JSON format', function() {
      expect(assignments.router).toHaveBeenCalledWith('/path', assignments.requestData,
        (assignments.body) ? JSON.parse(assignments.body) : undefined);
    });

    it('should write to the head of the response with the status', function() {
      expect(assignments.response.writeHead).toHaveBeenCalledWith(assignments.responseWriteHeadValue,
        assignments.evaluatedResponse.headers);
    });

    it('should write to the response using the evaluated response data', function() {
      expect(assignments.response.write).toHaveBeenCalledWith(assignments.responseWriteValue);
    });

    it('should call response.end', function() {
      expect(assignments.response.end).toHaveBeenCalled();
    });

    it('should call createServerResponse.listen with a port of ' + assignments.port, function() {
      expect(assignments.createServerResponse.listen).toHaveBeenCalledWith(assignments.port);
    });

    it('should call an anonomous function when the connection is made', function() {
      expect(assignments.server.on.calls.argsFor(0)).toEqual(['connection', jasmine.any(Function)]);
    });

    it('should call socket.setTimeout with a value of 4000', function() {
      expect(assignments.socket.setTimeout).toHaveBeenCalledWith(4000);
    });

    it('should call socket.on', function() {
      expect(assignments.socket.on.calls.count()).toEqual(assignments.socketCallbackCount);
    });

    it('should have a connection count of 1', function() {
      expect(assignments.webservice.getConnectionCount()).toEqual(assignments.connectionCount);
    });

    if (!https) {
      it('should not pass options into the createServer.bind call', function () {
        expect(assignments.request.createServer).not.toHaveBeenCalledWith(assignments.request, jasmine.any(Object));
      });
    } else {
      it('should pass options into the createServer.bind call', function () {
        expect(assignments.request.createServer.bind).toHaveBeenCalledWith(assignments.request, jasmine.any(Object));
      });
    }
  }

  function initializeModule(assignments) {
    assignments.webservice = webserviceModule(assignments.router, assignments.requestStore, assignments.mockState,
      assignments.config, assignments.request, url, assignments.logger, assignments.fsReadThen, Promise);
  }
});
