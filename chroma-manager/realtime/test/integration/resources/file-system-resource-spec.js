'use strict';

var getClient = require('../util/get-client');

describe('file system channel', function () {
  var client, fileSystemChannel;

  beforeEach(function () {
    client = getClient();

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
        statusCode: 200,
        body: jasmine.any(Object)
      });

      done();
    });

    fileSystemChannel.send('startStreaming');
  });

  it('should provide a httpGetList method', function (done) {
    fileSystemChannel.send('httpGetList', {}, function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });
});