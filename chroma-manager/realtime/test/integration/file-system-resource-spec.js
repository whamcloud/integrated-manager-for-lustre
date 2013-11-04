'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  Emitter = require('primus-emitter'),
  conf = require('../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('file system channel', function () {
  var client, fileSystemChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex,
      emitter: Emitter
    }});

    client = new Socket(conf.primusUrl);

    fileSystemChannel = client.channel('filesystem');
  });

  afterEach(function () {
    fileSystemChannel.end();
    client.end();
  });

  it('should call beforeStreaming once streaming is started', function (done) {
    fileSystemChannel.on('beforeStreaming', function (ack) {
      ack('httpGetList');
      done();
    });

    fileSystemChannel.send('startStreaming');
  });

  it('should stream data when everything is setup', function (done) {
    fileSystemChannel.on('beforeStreaming', function (ack) {
      ack('httpGetList');
    });

    fileSystemChannel.on('stream', function (data) {
      expect(data).toEqual({
        headers: jasmine.any(Object),
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });

    fileSystemChannel.send('startStreaming');
  });

  it('should provide a httpGetList method', function (done) {
    fileSystemChannel.send('httpGetList', {}, function (data) {
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