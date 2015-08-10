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


var λ = require('highland');
var _ = require('lodash-mixins');
var exec = require('child_process').exec;
var format = require('util').format;
var bufferString = require('through').bufferString;
var logger = require('./../logger');

module.exports = function reverseSourceMap (trace) {
  var lines = trace.split('\n');

  var logError = _.partialRight(logger.error.bind(logger), 'Reversing source map');
  var logErrorOnce = _.once(logError);

  return λ(lines)
    .map(function (line) {
      return λ(function generator (push) {
        var reverse = exec(format('node %s/reverse-source-map-line.js', __dirname), function (err, x) {
          if (err) {
            logErrorOnce(err);
            push(null, line + '\n');
          } else {
            push(null, x);
          }

          push(null, λ.nil);
        });

        reverse.stdin.write(line);
        reverse.stdin.end();
      });
    })
    .parallel(lines.length)
    .through(bufferString);
};
