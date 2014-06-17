'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  Emitter = require('primus-emitter'),
  conf = require('../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('notifications channel', function () {
  var client, notificationsChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex,
      emitter: Emitter
    }});

    client = new Socket(conf.primusUrl);

    notificationsChannel = client.channel('notification');
  });

  afterEach(function () {
    notificationsChannel.end();
    client.end();
  });

  it('should stream data when everything is setup', function (done) {
    notificationsChannel.on('beforeStreaming', function (ack) {
      ack('httpGetHealth');
    });

    notificationsChannel.on('stream', function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object),
        params: {}
      });

      done();
    });

    notificationsChannel.send('startStreaming');
  });

  it('should provide a httpGetHealth method', function (done) {
    notificationsChannel.send('httpGetHealth', {}, function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object),
        params: jasmine.any(Object)
      });

      done();
    });
  });
});
