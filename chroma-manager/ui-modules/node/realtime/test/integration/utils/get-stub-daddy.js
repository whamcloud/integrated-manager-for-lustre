'use strict';

var getStubDaddy = require('stub-daddy');
var conf = require('../../../conf');
var url = require('url');

module.exports = function invokeStubDaddy () {
  var stubDaddy = getStubDaddy();
  stubDaddy.config.port = url.parse(conf.get('SERVER_HTTP_URL')).port;

  return stubDaddy;
};
