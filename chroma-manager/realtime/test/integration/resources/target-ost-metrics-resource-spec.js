'use strict';

var getClient = require('../util/get-client');

describe('target ost metrics channel', function () {
  var client, targetOstMetricsChannel, params;

  beforeEach(function () {
    client = getClient();

    targetOstMetricsChannel = client.channel('targetostmetrics');

    params = {
      qs: {
        latest: true,
        metrics: 'stats_close'
      }
    };
  });

  afterEach(function () {
    targetOstMetricsChannel.end();
    client.end();
  });

  it('should call beforeStreaming once streaming is started', function (done) {
    targetOstMetricsChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics', params);
      done();
    });

    targetOstMetricsChannel.send('startStreaming');
  });

  it('should stream data when everything is setup', function (done) {
    targetOstMetricsChannel.on('beforeStreaming', function (ack) {
      ack('httpGetMetrics', params);
    });

    targetOstMetricsChannel.on('stream', function (data) {
      expect(data).toEqual({
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
        end: '2012-03-02T11:38:49.321Z',
        begin: '2012-03-02T11:28:49.321Z',
        metrics: 'stats_close'
      }
    };

    targetOstMetricsChannel.send('httpGetMetrics', params, function (data) {
      expect(data).toEqual({
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
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });
});