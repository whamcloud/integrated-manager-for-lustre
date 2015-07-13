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

  angular.module('models').factory('healthModel', ['alertModel', '$rootScope', 'STATES', 'interval', healthFactory]);

  /**
   * Determines current system health and broadcasts it.
   *
   * The health rules are:
   *
   * 1 or more active ERROR alerts: red
   * else: 1 or more active WARN alerts: amber
   * else: green
   *
   * @param {Object} alertModel
   * @param {Object} $rootScope
   * @param {Object} STATES
   * @param {Function} interval
   * @returns {Function}
   */
  function healthFactory (alertModel, $rootScope, STATES, interval) {
    /**
     * Looks for active warn or error alerts.
     */
    function getHealth () {
      // 1 or more active ERROR alerts: red else: 1 or more active WARN alerts: amber
      alertModel.query({
        active: true,
        severity__in: [STATES.WARN, STATES.ERROR],
        limit: 0
      }).$promise.then(broadcastHealth);
    }

    /**
     * Determines health by analyzing notification responses.
     * @param {Array} alerts
     */
    function broadcastHealth (alerts) {
      var states = [STATES.GOOD, STATES.WARN, STATES.ERROR];
      var health = [states.indexOf(STATES.GOOD)];

      // 1 or more active ERROR alerts: red else: 1 or more active WARN alerts: amber
      alerts.some(function (alertModel) {
        health.push(states.indexOf(alertModel.severity));

        return alertModel.severity === STATES.ERROR;
      });

      var currentHealth = Math.max.apply(null, health);

      $rootScope.$broadcast('health', {
        health: states[currentHealth],
        count: alerts.length
      });
    }

    return function start () {
      var clear = interval(getHealth, 10000, true);

      $rootScope.$on('checkHealth', getHealth);
      $rootScope.$on('$destroy', clear);
    };
  }
}());
