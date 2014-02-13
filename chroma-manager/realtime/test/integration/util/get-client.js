'use strict';

var Primus = require('primus'),
  multiplex = require('primus-multiplex'),
  Emitter = require('primus-emitter'),
  conf = require('../../../conf');

require('https').globalAgent.options.rejectUnauthorized = false;

module.exports = function getClient () {
  var Socket = Primus.createSocket({parser: 'JSON', transformer: 'socket.io', plugin: {
    multiplex: multiplex,
    emitter: Emitter
  }});

  return new Socket(conf.primusUrl);
};