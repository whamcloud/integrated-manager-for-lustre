'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  Emitter = require('primus-emitter'),
  conf = require('../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('host channel', function () {
  var client, hostChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex,
      emitter: Emitter
    }});

    client = new Socket(conf.primusUrl);

    hostChannel = client.channel('host');
  });

  afterEach(function () {
    hostChannel.end();
    client.end();
  });

  it('should call beforeStreaming once streaming is started', function (done) {
    hostChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics');
      done();
    });

    hostChannel.send('startStreaming');
  });

  it('should stream data when everything is setup', function (done) {
    var params = {
      qs: {
        latest: true,
        metrics: 'stats_close'
      }
    };

    hostChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics', params);
    });

    hostChannel.on('stream', function (data) {
      expect(data).toEqual({
        headers: jasmine.any(Object),
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });

    hostChannel.send('startStreaming');
  });

  it('should provide a httpGetMetrics method', function (done) {
    var params = {
      qs: {
        unit: 'minutes',
        size: 10,
        metrics: 'stats_close'
      }
    };

    hostChannel.send('httpGetMetrics', params, function (data) {
      expect(data).toEqual({
        headers: jasmine.any(Object),
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });

  it('should send an error to streamingError if params were not passed properly', function (done) {
    var params = {};

    hostChannel.on('streamingError', function (err) {
      expect(err).toEqual(jasmine.any(Object));

      done();
    });

    hostChannel.send('httpGetMetrics', params);
  });
});