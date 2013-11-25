'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  conf = require('../../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

describe('mds metric', function () {
  var client, mdsChannel;

  beforeEach(function () {
    var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
      multiplex: multiplex
    }});

    client = new Socket(conf.primusUrl);

    mdsChannel = client.channel('mds');
  });

  afterEach(function () {
    mdsChannel.end();
    client.end();
  });

  it('should write an error if query data is not written', function (done) {
    mdsChannel.write({ query: {} });

    mdsChannel.on('data', function errback(data) {
      expect(data.error).toBeTruthy();

      done();
    });
  });

  it('should write an error if no options object is written', function (done) {
    mdsChannel.write();

    mdsChannel.on('data', function errback(data) {
      expect(data.error).toBeTruthy();

      done();
    });
  });

  it('should write the data if options are provided properly', function (done) {
    mdsChannel.write({
      query: {
        unit: 'minutes',
        size: 10
      }
    });

    mdsChannel.on('data', function errback(data) {
      expect(data.data).toBeTruthy();

      done();
    });
  });
});