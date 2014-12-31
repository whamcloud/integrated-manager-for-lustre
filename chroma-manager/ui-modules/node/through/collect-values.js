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

/**
 * Collects values into an array.
 * This differs from λ.collect in that
 * we don't represent an empty stream as
 * an array. We only push an array with values.
 * @param {Highland.Stream} s
 * @returns {Highland.Stream} A stream.
 */
module.exports = function collectValues (s) {
  var arr = [];

  return s.consume(function collector (err, x, push, next) {
    if (err) {
      push(err);
      next();
    } else if (x === nil) {
      if (arr.length)
        push(null, arr);

      push(null, nil);
    } else {
      arr.push(x);
      next();
    }
  });
};
