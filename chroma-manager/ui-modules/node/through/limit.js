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

var _ = require('lodash-mixins');

/**
 * Determines if any items are truthy in the stream.
 * @param {Number} ms
 * @param {Highland.Stream} s
 * @returns {Highland.Stream} A stream.
 */
module.exports = _.curry(function limit (ms, s) {
  var underLimit = true;

  return s.consume(function (err, x, push, next) {
    if (err)
      pushNext(err, x);
    if (x === nil)
      push(null, nil);
    else
      pushNext(err, x);

    /**
     * Push token downstream and call next.
     * If we haven't ratelimited previously then push
     * immediately and call next.
     * Otherwise push and call next after limit ms.
     * @param {Error} err
     * @param {*} x
     */
    function pushNext (err, x) {
      if (underLimit) {
        underLimit = false;
        push(err, x);
        next();
      } else {
        setTimeout(function () {
          push(err, x);
          next();
        }, ms);
      }
    }
  });
});
