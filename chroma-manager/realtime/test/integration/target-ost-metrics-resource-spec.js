'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  Emitter = require('primus-emitter'),
  conf = require('../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('target ost metrics channel', function () {
  var client, targetOstMetricsChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex,
      emitter: Emitter
    }});

    client = new Socket(conf.primusUrl);

    targetOstMetricsChannel = client.channel('targetostmetrics');
  });

  afterEach(function () {
    targetOstMetricsChannel.end();
    client.end();
  });

  it('should call beforeStreaming once streaming is started', function (done) {
    targetOstMetricsChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics');
      done();
    });

    targetOstMetricsChannel.send('startStreaming');
  });

  it('should stream data when everything is setup', function (done) {
    var params = {
      qs: {
        latest: true,
        metrics: 'stats_close'
      }
    };

    targetOstMetricsChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics', params);
    });

    targetOstMetricsChannel.on('stream', function (data) {
      expect(data).toEqual({
        headers: jasmine.any(Object),
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });

    targetOstMetricsChannel.send('startStreaming');
  });

  it('should provide a httpGetMetrics method', function (done) {
    var params = {
      qs: {
        unit: 'minutes',
        size: 10,
        metrics: 'stats_close'
      }
    };

    targetOstMetricsChannel.send('httpGetMetrics', params, function (data) {
      expect(data).toEqual({
        headers: jasmine.any(Object),
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });

  it('should provide a httpGetList method', function (done) {
    targetOstMetricsChannel.send('httpGetList', {}, function (data) {
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

    targetOstMetricsChannel.on('streamingError', function (err) {
      expect(err).toEqual(jasmine.any(Object));

      done();
    });

    targetOstMetricsChannel.send('httpGetMetrics', params);
  });

  it('should provide a httpGetOstMetrics method', function (done) {
    var params = {
      qs: {
        latest: true,
        metrics: 'stats_close'
      }
    };

    targetOstMetricsChannel.send('httpGetOstMetrics', params, function (data) {
      expect(data).toEqual({
        headers: jasmine.any(Object),
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });
});