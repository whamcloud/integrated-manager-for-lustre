'use strict';

var utils = require('../../utils');
var start = require('../../../../index');
var clientErrorFixtures = require('../../fixtures/client-error');
var waitForRequests = require('../../../../request/request-agent').waitForRequests;

describe('source map reverse route', function () {
  var ack, socket, shutdown, stubDaddy;

  beforeEach(function (done) {
    stubDaddy = utils.getStubDaddy();

    stubDaddy.webService
      .startService()
      .done(done, done.fail);
  });

  beforeEach(function () {
    stubDaddy.inlineService
      .mock(clientErrorFixtures().reversedTrace);
  });

  beforeEach(function () {
    shutdown = start();
    socket = utils.getSocket();

    ack = jasmine.createSpy('ack');
    socket.emit('message1', clientErrorFixtures().originalTrace, ack);
  });

  beforeEach(function (done) {
    var timer = setInterval(function () {
      if (stubDaddy.inlineService.registeredMocks().data[0].remainingCalls === 0) {
        clearInterval(timer);
        done();
      }
    }, 1000);
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
      throw new Error(JSON.stringify(result.data, null, 2));
  });

  afterEach(function () {
    shutdown();
  });

  afterEach(waitForRequests);

  afterEach(function (done) {
    socket.on('disconnect', done);
    socket.close();
  });

  it('should reverse a trace', function () {
    expect(ack).toHaveBeenCalledOnceWith({
      data: clientErrorFixtures().reversedTrace.request.data.stack
    });
  });
});
