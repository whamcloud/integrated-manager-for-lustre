'use strict';

require('jasmine-n-matchers');

var getClient = require('./util/get-client');
var _ = require('lodash-mixins');
var registerMock = require('./util/register-mock');

describe('channel', function () {
  var client, channel;

  beforeEach(function (done) {
    registerMock({
      request: {
        method: 'GET',
        url: '/api/host/metric/?latest=true&metrics=stats_close',
        data: {
          latest: true,
          metrics: 'stats_close'
        },
        headers: {}
      },
      response: {
        status: 200,
        data: {},
        headers: {
          'content-type': 'application/json'
        }
      },
      expires: 0
    }, done);
  });

  beforeEach(function () {
    client = getClient();

    channel = client.channel('host');
  });

  afterEach(function () {
    channel.end();
    client.end();
  });

  it('should allow stop before start', function (done) {
    channel.send('stopStreaming', function (ack) {
      expect(ack).toBe('done');

      done();
    });
  });

  it('should toggle the stream', function (done) {
    var params = {
      qs: {
        latest: true,
        metrics: 'stats_close'
      }
    };

    var afterTwoCalls = _.after(2, function afterTwoCalls () {
      done();
    });

    var stopOnce = _.once(function stopOnce () {
      channel.send('stopStreaming', function () {
        channel.send('startStreaming');
      });
    });

    channel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics', params);

      stopOnce();
    });

    channel.send('startStreaming');

    channel.on('stream', function () {
      afterTwoCalls();
    });
  });
});
