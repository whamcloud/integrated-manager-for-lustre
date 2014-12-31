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
var _ = require('lodash-mixins');
var through = require('through');
var apiRequest = require('../../request/api');
var socketRouter = require('../index');
var pushSerializeError = require('../../request/push-serialize-error');

module.exports = function wildcardRoute () {
  socketRouter.all('/(.*)', function genericHandler (req, resp, next) {
    var options = _.extend({}, req.data, { method: req.verb.toUpperCase() });
    var request = _.partial(apiRequest, req.matches[0], options);

    var stream;

    if (resp.ack) {
      stream = request();

      stream.errors(pushSerializeError)
        .each(resp.ack.bind(resp.ack));
    } else {
      stream = λ(function generator (push, next) {
        request()
          .errors(pushSerializeError)
          .each(function pushData (x) {
            push(null, x);
            next();
          });
      });

      stream
        .ratelimit(1, 1000)
        .through(through.unchangedFilter)
        .each(resp.socket.emit.bind(resp.socket, req.messageName));
    }

    next(req, resp, stream);
  });
};
