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


angular.module('filters')
.filter('round', [function roundFilter () {
  'use strict';

  /**
   * Given a value and a number of places, rounds the number to at most that many places.
   * If trailing numbers are 0s they are truncated.
   *
   * Note: Javascript follows the IEEE 754 standard for it's number type. As such,
   * floating point accuracy cannot be guaranteed. Be warned, previous calculations may cause rounding
   * to be off by some small amount. See http://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html
   * for further explanation.
   *
   * @param {Number} value The number to round.
   * @param {Number} places The number of places to round.
   */
  return function rounder (value, places) {
    // Return value if number is not as expected.
    if (isNaN(parseFloat(value)) || !isFinite(value)) return value;
    // If places is not provided, just round the value to nearest whole number.
    if (places == null) return Math.round(value);

    var shiftTo = Math.pow(10, places);

    // Shift
    value = Math.round(value * shiftTo);

    // Shift back
    return value / shiftTo;
  };
}]);
