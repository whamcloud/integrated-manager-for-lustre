'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  conf = require('../../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('ost balance metric', function () {
  var client, ostChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex
    }});

    client = new Socket(conf.primusUrl);

    ostChannel = client.channel('ostbalance');
  });

  afterEach(function () {
    ostChannel.end();
    client.end();
  });

  it('should write an error if no options object is written', function (done) {
    ostChannel.write();

    ostChannel.on('data', function errback(data) {
      expect(data.error).toBeTruthy();

      done();
    });
  });

  it('should write the data if options are provided properly', function (done) {
    ostChannel.write({
      query: {
        unit: 'minutes',
        size: 10
      }
    });

    ostChannel.on('data', function callback(data) {
      expect(data.data).toBeTruthy();

      done();
    });
  });
});