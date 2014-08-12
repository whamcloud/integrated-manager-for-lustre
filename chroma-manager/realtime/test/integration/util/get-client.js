'use strict';

var Primus = require('primus');
var multiplex = require('primus-multiplex');
var Emitter = require('primus-emitter');
var conf = require('../../../conf');
var errorSerializer = require('bunyan/lib/bunyan').stdSerializers.err;
var MultiplexSpark = require('primus-multiplex/lib/server/spark');
var primusServerWriteFactory = require('../../../primus-server-write');
var primusServerWrite = primusServerWriteFactory(errorSerializer, MultiplexSpark);

require('https').globalAgent.options.rejectUnauthorized = false;

module.exports = function getClient () {
  var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
    multiplex: multiplex,
    emitter: Emitter,
    serverWrite: primusServerWrite
  }});

  return new Socket(conf.primusUrl);
};
