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

  angular.module('primus', [])
    .value('Primus', window.Primus)
    .value('WebSocket', window.WebSocket)
    .factory('primus', ['$window', '$applyFunc', 'WebSocket', 'Primus', 'BASE', 'disconnectModal', primusFactory]);

  function primusFactory ($window, $applyFunc, WebSocket, Primus, BASE, disconnectModal) {
    var primus, modal;

    /**
     * Lazy. Returns a new connection or the existing one.
     * @returns {Object}
     */
    return function get () {
      if (primus) return primus;

      primus = new Primus(BASE + ':' + $window.location.port);

      primus.on('reconnecting', $applyFunc(function onReconnecting() {
        if (!modal)
          modal = disconnectModal();
      }));

      primus.on('reconnected', $applyFunc(function onReconnected() {
        if (modal) {
          modal.close();
          modal = null;
        }
      }));

      /**
       * If primus itself has an error, let's show it and end the connection.
       * @param {Object} err The error.
       */
      primus.on('error', $applyFunc(function onError (err) {
        // If the error is an unhelpful WebSocket.prototype.onError event
        // without a message do nothing.
        // Otherwise we will throw an error when we should just do a disconnect.
        if (err.target instanceof WebSocket && !err.message)
          return;

        primus.end();

        throw err;
      }));

      return primus;
    };
  }

  angular.module('primus').factory('$applyFunc', ['$rootScope', $applyFuncFactory]);

  /**
   * Generates an apply HOF.
   * @param {Object} $rootScope
   * @returns {Function}
   */
  function $applyFuncFactory ($rootScope) {
    /**
     * HOF. Returns a function that when called
     * might invoke $apply if we are not in $$phase.
     * @param {Function} func
     * @returns {Function}
     */
    return function $applyFunc (func) {
      return function $innerApplyFunc () {
        var args = arguments;

        if (!$rootScope.$$phase)
          return $rootScope.$apply(apply);
        else
          return apply();

        function apply () {
          return func.apply(null, args);
        }
      };
    };
  }
}());
