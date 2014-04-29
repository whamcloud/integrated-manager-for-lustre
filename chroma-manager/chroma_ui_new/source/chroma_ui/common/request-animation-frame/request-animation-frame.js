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


(function () {
  'use strict';

  var vendors = ['webkit', 'moz'];

  angular.module('requestAnimationFrame')
    .factory('requestAnimationFrame', ['$window', function ($window) {
      var requestAnimationFrame = $window.requestAnimationFrame;
      var lastTime = 0;

      if (!requestAnimationFrame)
        vendors.some(function (vendor) {
          return (requestAnimationFrame = $window[vendor + 'RequestAnimationFrame']);
        });

      if (!requestAnimationFrame)
        requestAnimationFrame = function(callback) {
          var currTime = new Date().getTime();
          var timeToCall = Math.max(0, 16 - (currTime - lastTime));
          var id = $window.setTimeout(function() { callback(currTime + timeToCall); },
            timeToCall);
          lastTime = currTime + timeToCall;
          return id;
        };

      return requestAnimationFrame.bind($window);
    }])
    .factory('cancelAnimationFrame', ['$window', function ($window) {
      var cancelAnimationFrame = $window.cancelAnimationFrame;

      if (!cancelAnimationFrame)
        vendors.some(function (vendor) {
          return (cancelAnimationFrame =
            $window[vendor + 'CancelAnimationFrame'] || $window[vendor + 'CancelRequestAnimationFrame']);
        });

      if (!cancelAnimationFrame)
        cancelAnimationFrame = function(id) {
          $window.clearTimeout(id);
        };

      return cancelAnimationFrame.bind($window);
    }])
    .factory('raf', ['requestAnimationFrame', 'cancelAnimationFrame',
      function (requestAnimationFrame, cancelAnimationFrame) {
        return {
          requestAnimationFrame: requestAnimationFrame,
          cancelAnimationFrame: cancelAnimationFrame
        };
      }
    ]);
}());

