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

var _ = require('lodash-mixins');
var apiRequest = require('../../request/api');
var socketRouter = require('../index');
var pushSerializeError = require('../../request/push-serialize-error');
var reverseSourceMap = require('../../reverse-source-map');
var logger = require('../../logger');

module.exports = function srcmapReverseRoute () {
  socketRouter.post('/srcmap-reverse', function srcmapReverseHandler (req, resp, next) {
    var reversedStream = reverseSourceMap(req.data.stack);

    reversedStream
      .observe()
      .map(function recordToApi (stack) {
        var headers = req.data.headers;
        delete req.data.headers;

        req.data.stack = stack;

        return {
          method: 'POST',
          json: req.data,
          headers: headers
        };
      })
      .flatMap(apiRequest('/client_error'))
      .stopOnError(function (err) {
        logger.error(err);
      })
      .each(_.noop);

    reversedStream
      .map(function setData (stack) {
        return { data: stack };
      })
      .stopOnError(pushSerializeError)
      .each(resp.ack.bind(resp));

    next(req, resp, reversedStream);
  });
};
