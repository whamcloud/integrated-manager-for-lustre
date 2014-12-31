'use strict';

var utils = require('../../utils');
var getAlertFixtures = require('../../fixtures/alert');
var start = require('../../../../index');
var waitForRequests = require('../../../../request/request-agent').waitForRequests;

describe('wildcard route', function () {
  var socket, stubDaddy, alertFixtures, alertRequest, shutdown, emitMessage, onceMessage;

  beforeEach(function () {
    alertFixtures = getAlertFixtures();

    alertRequest = {
      path: '/alert',
      options: {
        qs: {
          active: 'true',
          severity__in: [
            'WARNING',
            'ERROR'
          ],
          limit: 0
        }
      }
    };
  });

  beforeEach(function (done) {
    stubDaddy = utils.getStubDaddy();

    stubDaddy.webService
      .startService()
      .done(done, done.fail);
  });

  beforeEach(function () {
    shutdown = start();
    socket = utils.getSocket();
    emitMessage = socket.emit.bind(socket, 'message1');
    onceMessage = socket.once.bind(socket, 'message1');
  });

  afterEach(function (done) {
    stubDaddy.webService
      .stopService()
      .done(done, done.fail);
  });

  afterEach(function () {
    var result = stubDaddy.inlineService
      .mockState();

    if (result.status !== 200)
      throw new Error(result.data);
  });

  afterEach(function () {
    shutdown();
  });

  afterEach(waitForRequests);

  afterEach(function (done) {
    socket.on('disconnect', done);
    socket.close();
  });

  describe('handling response', function () {
    beforeEach(function () {
      stubDaddy.inlineService.mock(alertFixtures.yellowHealth);
    });

    it('should provide an ack', function (done) {
      emitMessage(alertRequest, function ack (resp) {
        expect(resp).toEqual(alertFixtures.yellowHealth.response.data);
        done();
      });
    });

    it('should provide an event', function (done) {
      emitMessage(alertRequest);
      onceMessage(function onData (resp) {
        expect(resp).toEqual(alertFixtures.yellowHealth.response.data);
        done();
      });
    });

    describe('handling post with json-mask', function () {
      describe('on a valid match', function () {
        beforeEach(function () {
          alertRequest.options.jsonMask = 'objects/(id,active)';
        });

        it('should filter the response to only the parameters specified in the json mask', function (done) {
          emitMessage(alertRequest, function ack (resp) {
            expect(resp).toEqual({
              objects: [
                {
                  id: '2',
                  active: false
                }
              ]
            });

            done();
          });
        });
      });

      describe('on an invalid match', function () {
        beforeEach(function () {
          alertRequest.options.jsonMask = 'objects/(invalid)';
        });

        it('should throw an exception', function (done) {
          emitMessage(alertRequest, function ack (resp) {
            expect(resp).toEqual({
              error: {
                message: 'The json mask did not match the response and as a result returned null. Examine the mask: ' +
                '"objects/(invalid)" From GET request to /alert',
                name: 'Error',
                stack: jasmine.any(String),
                statusCode: 400
              }
            });
            done();
          });
        });
      });
    });
  });

  describe('handling errors', function () {
    beforeEach(function () {
      stubDaddy.inlineService.mock({
        request: {
          method: 'GET',
          url: '/api/throw-error/',
          data: {},
          headers: {}
        },
        response: {
          status: 500,
          headers: {},
          data: {
            err: { cause: 'boom!' }
          }
        },
        expires: 0,
        dependencies: []
      });
    });

    it('should ack an error', function (done) {
      emitMessage({ path: '/throw-error' }, function ack (resp) {
        expect(resp).toEqual({
          error: {
            message: '{"err":{"cause":"boom!"}} From GET request to /throw-error',
            name: 'Error',
            stack: jasmine.any(String),
            statusCode: 500
          }
        });
        done();
      });
    });

    it('should send an error through events', function (done) {
      emitMessage({ path: '/throw-error' });
      onceMessage(function onData (resp) {
        expect(resp).toEqual({
          error: {
            message: '{"err":{"cause":"boom!"}} From GET request to /throw-error',
            name: 'Error',
            stack: jasmine.any(String),
            statusCode: 500
          }
        });
        done();
      });
    });
  });
});
