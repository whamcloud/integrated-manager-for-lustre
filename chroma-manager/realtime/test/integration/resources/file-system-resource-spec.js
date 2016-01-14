'use strict';

var getClient = require('../util/get-client');
var registerMock = require('../util/register-mock');

describe('file system channel', function () {
  var client, fileSystemChannel;

  beforeEach(function (done) {
    registerMock({
      request: {
        method: 'GET',
        url: '/api/filesystem/',
        data: {},
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
        body: jasmine.any(Object),
        params: {}
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
