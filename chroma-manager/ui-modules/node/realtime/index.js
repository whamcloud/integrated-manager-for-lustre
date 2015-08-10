//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.

'use strict';

var createIo = require('socket.io');
var socketRouter = require('./socket-router');
var requestValidator = require('./request-validator');
var serializeError = require('./request/serialize-error');
var eventWildcard = require('./event-wildcard');
var conf = require('./conf');
var logger = require('./logger');
var _ = require('lodash-mixins');

// Don't limit to pool to 5 in node 0.10.x
var https = require('https');
var http = require('http');
https.globalAgent.maxSockets = http.globalAgent.maxSockets = Infinity;

var qs = require('querystring');
var url = require('url');

module.exports = function start () {
  var io = createIo();
  io.use(eventWildcard);
  io.attach(conf.get('REALTIME_PORT'));

  var isMessage = /message(\d+)/;

  io.on('connection', function (socket) {
    logger.debug('socket connected');

    socket.on('*', function onData (data, ack) {
      var matches = isMessage.exec(data.eventName);

      if (!matches)
        return;

      handleRequest(data, socket, ack, matches[1]);
    });

    socket.on('error', function onError (err) {
      logger.error({ err: err }, 'socket error');
    });
  });

  function handleRequest (data, socket, ack, id) {
    try {
      var errors = requestValidator(data);

      if (errors.length)
        throw new Error(errors);

      var options = data.options || {};
      var method = (typeof options.method !== 'string' ? 'get' : options.method);

      var parsedUrl = url.parse(data.path);
      var qsObj =  { qs: qs.parse(parsedUrl.query) };

      _.merge(options, qsObj);

      socketRouter.go(parsedUrl.pathname,
        { verb: method, data: options, messageName: data.eventName, endName: 'end' + id },
        { socket: socket, ack: ack }
      );
    } catch (error) {
      error.statusCode = 400;
      var err = serializeError(error);

      if (ack)
        ack(err);
      else
        socket.emit(data.eventName, err);
    }
  }

  return function shutdown () {
    io.close();
  };
};
