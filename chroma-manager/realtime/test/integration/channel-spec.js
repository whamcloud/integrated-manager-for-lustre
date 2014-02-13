'use strict';

require('jasmine-n-matchers');

var getClient = require('./util/get-client'),
  _ = require('lodash');

describe('channel', function () {
  var client, channel;

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