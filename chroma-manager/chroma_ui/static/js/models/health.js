//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function () {
  'use strict';

  /*
   Color rules:
   1 or more ERROR alerts are active: red
   else: 1 or more WARN alerts are active: amber
   1 or more WARN alerts are inactive but have not been dismissed: amber
   1 or more unacknowledged WARN or higher events: amber
   1 or more unacknowledged failed commands: amber
   else: green
   */

  function healthFactory (alertModel, commandModel, eventModel, $timeout, $q, $rootScope, ERROR, WARN, GOOD) {
    var events, alerts, inactiveAlerts, commands;

    $timeout(function timesUp() {
      getHealth();

      $timeout(timesUp, 30000);
    }, 0);

    $rootScope.$on('checkHealth', getHealth);

    /**
     * Loads the relevant services.
     */
    function getHealth () {
      events = eventModel.loadAll({dismissed: false, severity__in: [WARN, ERROR], limit: 1});
      alerts = alertModel.loadAll({active: true, severity__in: [WARN, ERROR]});
      inactiveAlerts = alertModel.loadAll({active: false, severity__in: [WARN], limit: 1});
      commands = commandModel.loadAll({errored: true, dismissed: false, limit: 1});

      $q.all([events.__promise, alerts.__promise, commands.__promise]).then(broadcastHealth);
    }

    /**
     * Checks the relevant services for status and calls broadcast with the results.
     */
    function broadcastHealth () {
      var states = [GOOD, WARN, ERROR];
      var health = [states.indexOf(GOOD)];

      events.forEach(function () {
        health.push(states.indexOf(WARN));
      });

      alerts.some(function (alertModel) {
        health.push(states.indexOf(alertModel.severity));

        return alertModel.severity === ERROR;
      });

      [inactiveAlerts, commands].forEach(function (group) {
        if (group.length) {
          health.push(states.indexOf(WARN));
        }
      });

      health = _.unique(health);

      var currentHealth = Math.max.apply(null, health);

      $rootScope.$broadcast('health', states[currentHealth]);
    }
  }

  var deps = [
    'alertModel', 'commandModel', 'eventModel',
    '$timeout', '$q', '$rootScope',
    'ERROR', 'WARN', 'GOOD',
    healthFactory
  ];
  angular.module('models').factory('healthModel', deps);
}());
