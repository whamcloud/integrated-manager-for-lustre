'use strict';

var Q = require('q');
var requestFactory = require('../../request');
var jsonMask = require('json-mask');
var VERBS = require('socket-router').verbs;

describe('request', function () {
  var conf, patchedRequest, requestInstance, request, logger;

  beforeEach(function () {
    spyOn(Q, 'ninvoke').andCallThrough();
    spyOn(Q, 'spread').andCallThrough();
    spyOn(Q.makePromise.prototype, 'finally').andCallThrough();
    spyOn(Q.makePromise.prototype, 'then').andCallThrough();

    conf = {
      apiUrl: 'https://fake.com/api/'
    };

    requestInstance = {
      get: jasmine.createSpy('get'),
      post: jasmine.createSpy('post'),
      delete: jasmine.createSpy('delete'),
      patch: jasmine.createSpy('patch'),
      put: jasmine.createSpy('put')
    };

    patchedRequest = {
      defaults: jasmine.createSpy('request.defaults').andReturn(requestInstance)
    };

    logger = {
      child: jasmine.createSpy('child').andReturn({
        info: jasmine.createSpy('log.info'),
        debug: jasmine.createSpy('log.debug'),
        trace: jasmine.createSpy('log.trace'),
        error: jasmine.createSpy('log.error')
      })
    };

    request = requestFactory(conf, patchedRequest, logger, Q, jsonMask, VERBS);
  });

  it('should setup a default request', function () {
    expect(patchedRequest.defaults).toHaveBeenCalledOnceWith({
      json: true,
      strictSSL: false,
      useQuerystring: true,
      timeout: 60000, // 1 minute
      pool: {
        maxSockets: 20
      }
    });
  });

  it('should return an object of verbs to methods', function () {
    expect(request).toContainObject({
      get: jasmine.any(Function),
      post: jasmine.any(Function),
      delete: jasmine.any(Function),
      patch: jasmine.any(Function),
      put: jasmine.any(Function)
    });
  });

  var verbList = Object.keys(VERBS)
    .map(function getVerb (key) {
      return VERBS[key];
    });

  verbList.forEach(function testVerb (verb) {
    describe('error handling for ' + verb, function () {
      var promise;

      beforeEach(function () {
        requestInstance[verb].andCallFake(function fake (url, options, cb) {
          cb(null, {
            request: {},
            statusCode: 400,
            body: 'foo is not bar.'
          }, 'foo is not bar.');
        });

        promise = request[verb]('/foo/bar');
      });

      it('should be an error', function (done) {
        promise
          .catch(function assertError (err) {
            expect(err).toEqual(jasmine.any(Error));
          })
          .done(done);
      });

      it('should have the status code', function (done) {
        promise
          .catch(function assertError (err) {
            expect(err.statusCode).toBe(400);
          })
          .done(done);
      });

      it('should have the error message', function (done) {
        promise
          .catch(function assertError (err) {
            expect(err.message).toContain('"foo is not bar."');
          })
          .done(done);
      });
    });

    it('should strip leading slashes from the path for ' + verb , function () {
      request[verb]('/foo/bar/');

      expect(Q.ninvoke).toHaveBeenCalledOnceWith(requestInstance, verb, 'https://fake.com/api/foo/bar/', {});
    });

    it('should add a trailing slash to the path for ' + verb, function () {
      request[verb]('/foo/bar');

      expect(Q.ninvoke).toHaveBeenCalledOnceWith(requestInstance, verb, 'https://fake.com/api/foo/bar/', {});
    });

    it('should resolve with the successful response for ' + verb, function (done) {
      var response = {
        request: {},
        statusCode: 200,
        body: {status: 'foo is foo.'}
      };

      requestInstance[verb].andCallFake(function fake (url, options, cb) {
        cb(null, response, response.body);
      });

      request[verb]('/foo/bar')
        .then(function (resp) {
          expect(resp).toEqual(response);
        })
        .done(done);
    });

    it('should mask params for ' + verb, function (done) {
      var serverResponse = {
        request: {},
        statusCode: 200,
        body: {
          foo: 'bar',
          baz: 'bat'
        }
      };

      requestInstance[verb].andCallFake(function fake (url, options, cb) {
        cb(null, serverResponse, serverResponse.body);
      });

      request[verb]('/foo/bar', {jsonMask: 'baz'})
        .then(function gotResponse(resp) {
          expect(resp.body).toEqual({baz: 'bat'});
        })
        .done(done);
    });
  });
});
