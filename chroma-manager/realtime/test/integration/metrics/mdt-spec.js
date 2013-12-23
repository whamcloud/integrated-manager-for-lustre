'use strict';

jasmine.getEnv().defaultTimeoutInterval = 10000;

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  conf = require('../../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('mdt metric', function () {
  var client, mdtChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex
    }});

    client = new Socket(conf.primusUrl);

    mdtChannel = client.channel('mdt');
  });

  afterEach(function () {
    mdtChannel.end();
    client.end();
  });

  it('should write an error if query data is not written', function (done) {
    mdtChannel.write({ query: {} });

    mdtChannel.on('data', function errback(data) {
      expect(data.error).toBeTruthy();

      done();
    });
  });

  it('should write an error if no options object is written', function (done) {
    mdtChannel.write();

    mdtChannel.on('data', function errback(data) {
      expect(data.error).toBeTruthy();

      done();
    });
  });

  it('should write the data if options are provided properly', function (done) {
    mdtChannel.write({
      query: {
        unit: 'minutes',
        size: 10
      }
    });

    mdtChannel.on('data', function callback(data) {
      expect(data.data).toBeTruthy();

      done();
    });
  });
});
