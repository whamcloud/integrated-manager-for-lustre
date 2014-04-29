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


(function (_) {
  'use strict';

  /*
   Color rules:
   1 or more unacknowledged WARN or higher events: amber

   1 or more ERROR alerts are active: red
   else: 1 or more WARN alerts are active: amber

   1 or more WARN alerts are inactive but have not been dismissed: amber

   1 or more unacknowledged failed commands: amber
   else: green
   */

  function healthFactory(alertModel, commandModel, eventModel, $q, $rootScope, STATES, interval) {
    var events, alerts, inactiveAlerts, commands;


    /**
     * Loads the relevant services.
     */
    function getHealth() {
      //1 or more unacknowledged WARN or higher events: amber
      events = eventModel.query({dismissed: false, severity__in: [STATES.WARN, STATES.ERROR], limit: 1});

      //1 or more ERROR alerts are active: red else: 1 or more WARN alerts are active: amber
      alerts = alertModel.query({active: true, severity__in: [STATES.WARN, STATES.ERROR], limit: 0});

      //1 or more WARN alerts are inactive but have not been dismissed: amber
      inactiveAlerts = alertModel.query({active: false, dismissed: false, severity__in: [STATES.WARN], limit: 1});

      //1 or more unacknowledged failed commands: amber
      commands = commandModel.query({errored: true, dismissed: false, limit: 1});

      $q.all([events.$promise, alerts.$promise, inactiveAlerts.$promise, commands.$promise]).then(broadcastHealth);
    }

    /**
     * Checks the relevant services for status and calls broadcast with the results.
     */
    function broadcastHealth() {
      var states = [STATES.GOOD, STATES.WARN, STATES.ERROR];
      var health = [states.indexOf(STATES.GOOD)];

      //1 or more unacknowledged WARN or higher events: amber
      events.forEach(function () {
        health.push(states.indexOf(STATES.WARN));
      });

      //1 or more ERROR alerts are active: red else: 1 or more WARN alerts are active: amber
      alerts.some(function (alertModel) {
        health.push(states.indexOf(alertModel.severity));

        return alertModel.severity === STATES.ERROR;
      });

      // 1 or more WARN alerts are inactive but have not been dismissed: amber
      // 1 or more unacknowledged failed commands: amber
      [inactiveAlerts, commands].forEach(function (group) {
        if (group.length) {
          health.push(states.indexOf(STATES.WARN));
        }
      });

      health = _.unique(health);

      var currentHealth = Math.max.apply(null, health);

      $rootScope.$broadcast('health', states[currentHealth]);
    }

    return function start() {
      var clear = interval(getHealth, 10000, true);

      $rootScope.$on('checkHealth', getHealth);
      $rootScope.$on('$destroy', clear);
    };
  }

  angular.module('models').factory('healthModel',
    ['alertModel', 'commandModel', 'eventModel', '$q', '$rootScope', 'STATES', 'interval', healthFactory]
  );
}(window.lodash));
