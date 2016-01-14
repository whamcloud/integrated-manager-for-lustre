'use strict';

var Primus = require('primus');
var multiplex = require('primus-multiplex');
var Emitter = require('primus-emitter');
var conf = require('../../conf');
var registerMock = require('./util/register-mock');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('notifications channel', function () {
  var client, notificationsChannel;

  beforeEach(function (done) {
    registerMock({
      request: {
        method: 'GET',
        url: '/api/alert/',
        data: {},
        headers: {}
      },
      response: {
        status: 200,
        data: {
          objects: []
        },
        headers: {
          'content-type': 'application/json'
        }
      },
      expires: 0
    }, done);
  });

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
