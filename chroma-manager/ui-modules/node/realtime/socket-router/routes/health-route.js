//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

var λ = require('highland');
var through = require('through');
var apiRequest = require('../../request/api');
var socketRouter = require('../index');
var pushSerializeError = require('../../request/push-serialize-error');

var STATES;
exports.STATES = STATES = {
  ERROR: 'ERROR',
  WARN: 'WARNING',
  GOOD: 'GOOD'
};

module.exports = function healthRoutes () {
  socketRouter.get('/health', function getHealth (req, resp, next) {
    var stream = λ(function generator (push, next) {
      var alertStream = apiRequest('alert/', {
        qs: {
          active: true,
          severity__in: [STATES.WARN, STATES.ERROR],
          limit: 0
        }
      })
        .pluck('objects')
        .flatten()
        .pluck('severity')
        .compact();

      // Calculates the health of the endpoint.
      var health = alertStream
        .uniq()
        .otherwise([STATES.GOOD])
        .through(through.sortBy(function compare (a, b) {
          var states = [STATES.GOOD, STATES.WARN, STATES.ERROR];

          return states.indexOf(a) - states.indexOf(b);
        }))
        .last();

      // Counts all items in the stream.
      var count = alertStream
        .observe()
        .reduce(0, λ.add(1));

      λ([health, count])
        .sequence()
        .through(through.zipObject(['health', 'count']))
        .errors(pushSerializeError)
        .each(function pushAndTurn (x) {
          push(null, x);
          next();
        });
    });

    stream
      .ratelimit(1, 1000)
      .through(through.unchangedFilter)
      .each(resp.socket.emit.bind(resp.socket, req.messageName));

    next(req, resp, stream);
  });
};
