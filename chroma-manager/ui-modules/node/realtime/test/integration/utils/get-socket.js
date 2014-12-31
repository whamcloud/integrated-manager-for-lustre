'use strict';
var client = require('../../../node_modules/socket.io/node_modules/socket.io-client');
var conf = require('../../../conf');
var format = require('util').format;

module.exports = function invokeSocket () {
  return client(format('http://localhost:%s', conf.get('REALTIME_PORT')), {
    forceNew: true
  });
};
