'use strict';

var utils = require('../../utils');
var getAlertFixtures = require('../../fixtures/alert');
var start = require('../../../../index');
var waitForRequests = require('../../../../request/request-agent').waitForRequests;

describe('health route', function () {
  var socket, stubDaddy, alertFixtures, shutdown, messageName, emitMessage, onceMessage, onMessage;

  beforeEach(function () {
    messageName = 'message1';
    alertFixtures = getAlertFixtures();
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
    emitMessage = socket.emit.bind(socket, messageName, { path: '/health' });
    onceMessage = socket.once.bind(socket, messageName);
    onMessage = socket.on.bind(socket, messageName);
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

  describe('no alerts', function () {
    beforeEach(function () {
      stubDaddy.inlineService
        .mock(alertFixtures.greenHealth);
    });

    it('should return good health', function (done) {
      emitMessage();
      onceMessage(function (data) {
        expect(data.health).toBe('GOOD');
        done();
      });
    });

    it('should return a count of alerts', function (done) {
      emitMessage();
      onceMessage(function (data) {
        expect(data.count).toEqual(0);
        done();
      });
    });
  });

  describe('warning alerts', function () {
    beforeEach(function () {
      stubDaddy.inlineService
        .mock(alertFixtures.yellowHealth);
    });

    it('should return warning health', function (done) {
      emitMessage();

      onceMessage(function (data) {
        expect(data.health).toBe('WARNING');
        done();
      });
    });

    it('should return a count of alerts', function (done) {
      emitMessage();

      onceMessage(function (data) {
        expect(data.count).toEqual(1);
        done();
      });
    });
  });

  describe('error alerts', function () {
    beforeEach(function () {
      stubDaddy.inlineService
        .mock(alertFixtures.redHealth);
    });

    it('should return error health', function (done) {
      emitMessage();

      onceMessage(function (data) {
        expect(data.health).toBe('ERROR');
        done();
      });
    });

    it('should return a count of alerts', function (done) {
      emitMessage();

      onceMessage(function (data) {
        expect(data.count).toEqual(1);
        done();
      });
    });
  });

  describe('warning + error alerts', function () {
    beforeEach(function () {
      alertFixtures.redHealth.response.data.objects.splice(1, 0, alertFixtures.yellowHealth.response.data.objects[0]);

      stubDaddy.inlineService
        .mock(alertFixtures.redHealth);
    });

    it('should return error health', function (done) {
      emitMessage();

      onceMessage(function (data) {
        expect(data.health).toBe('ERROR');
        done();
      });
    });

    it('should return a count of alerts', function (done) {
      emitMessage();

      onceMessage(function (data) {
        expect(data.count).toEqual(2);
        done();
      });
    });
  });

  it('should send two responses', function (done) {
    var greenHealth = utils.clone(alertFixtures.greenHealth);
    greenHealth.expires = 1;

    stubDaddy.inlineService
      .mock(greenHealth);

    stubDaddy.inlineService
      .mock(alertFixtures.yellowHealth);

    var messages = [];

    emitMessage();

    onMessage(function (data) {
      messages.push(data);

      if (messages.length === 2) {
        expect(messages).toEqual([
          { health: 'GOOD', count: 0 },
          { health: 'WARNING', count: 1 }
        ]);
        done();
      }
    });
  });

  it('should send error', function (done) {
    var redHealth = utils.clone(alertFixtures.redHealth);

    redHealth.response.status = 500;
    redHealth.response.data = { err: 'boom!' };

    stubDaddy.inlineService
      .mock(redHealth);

    emitMessage();

    onceMessage(function (data) {
      expect(data).toEqual({
        error: {
          name: 'Error',
          message: '{"err":"boom!"} From GET request to alert/',
          stack: jasmine.any(String),
          statusCode: 500
        }
      });
      done();
    });
  });
});
