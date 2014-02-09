'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  Emitter = require('primus-emitter'),
  conf = require('../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('target channel', function () {
  var client, targetChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex,
      emitter: Emitter
    }});

    client = new Socket(conf.primusUrl);

    targetChannel = client.channel('target');
  });

  afterEach(function () {
    targetChannel.end();
    client.end();
  });

  it('should call beforeStreaming once streaming is started', function (done) {
    targetChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics');
      done();
    });

    targetChannel.send('startStreaming');
  });

  it('should stream data when everything is setup', function (done) {
    var params = {
      qs: {
        latest: true,
        metrics: 'stats_close'
      }
    };

    targetChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics', params);
    });

    targetChannel.on('stream', function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });

    targetChannel.send('startStreaming');
  });

  it('should provide a httpGetMetrics method', function (done) {
    var params = {
      qs: {
        unit: 'minutes',
        size: 10,
        metrics: 'stats_close'
      }
    };

    targetChannel.send('httpGetMetrics', params, function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });

  it('should provide a httpGetList method', function (done) {
    targetChannel.send('httpGetList', {}, function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });

  it('should send an error to streamingError if params were not passed properly', function (done) {
    var params = {};

    targetChannel.on('streamingError', function (err) {
      expect(err).toEqual(jasmine.any(Object));

      done();
    });

    targetChannel.send('httpGetMetrics', params);
  });
});