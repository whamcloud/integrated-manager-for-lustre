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


(function () {
  'use strict';

  angular.module('timing', []).factory('interval', ['$window', '$rootScope', function ($window, $rootScope) {
    /**
     * This function is a simple wrapper around set interval, mostly to aid testing.
     * @param {function} func The function to call.
     * @param {number} delay The number of milliseconds to delay the interval call.
     * @param {Boolean} [callBeforeDelay] Should func be called before the delay? Defaults to false.
     * @returns {function} A function that can be called to clear this interval.
     */
    return function run(func, delay, callBeforeDelay) {
      function runFunc() {
        $rootScope.safeApply(func);
      }

      if (callBeforeDelay) {
        runFunc();
      }

      var intervalId = $window.setInterval(runFunc, delay);

      return function clear() {
        $window.clearInterval(intervalId);
      };
    };
  }]);
}());
