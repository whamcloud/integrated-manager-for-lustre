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

var inherits = require('util').inherits;
var _ = require('lodash');

var STATES;
exports.STATES = STATES = {
  ERROR: 'ERROR',
  WARN: 'WARNING',
  GOOD: 'GOOD',
  INFO: 'INFO',
  INCOMPLETE: 'INCOMPLETE',
  CANCELED: 'CANCELED',
  COMPLETE: 'COMPLETE'
};

exports.notificationResourceFactory = notificationResourceFactory;

function notificationResourceFactory (Resource, AlertResource) {
  var alertResource = new AlertResource();

  /**
   * Extension of Resource.
   * @constructor
   * @extends Resource
   */
  function NotificationResource () {
    Resource.call(this, 'notification');
  }

  inherits(NotificationResource, Resource);

  /**
   * Returns a promise representing the current system health.
   * The rules to determine health are:
   *
   * 1 or more active ERROR alerts: red
   * else: 1 or more active WARN alerts: amber
   * else: green
   *
   * @param {Object} params
   * @returns {Q.promise}
   */
  NotificationResource.prototype.httpGetHealth = function httpGetHealth (params) {
    return alertResource.httpGetList(_.merge({}, params, {
      qs: {
        active: true,
        severity__in: [STATES.WARN, STATES.ERROR],
        limit: 0
      }
    }))
      .then(allDone);

    /**
     * Takes the response and uses it to determine system health.
     * @param {Object} alertResponse
     * @returns {Object}
     */
    function allDone (alertResponse) {
      var alerts = alertResponse.body.objects;

      var states = [STATES.GOOD, STATES.WARN, STATES.ERROR];
      var health = [states.indexOf(STATES.GOOD)];

      // 1 or more active ERROR alerts: red else: 1 or more active WARN alerts: amber
      alerts.some(function (alert) {
        health.push(states.indexOf(alert.severity));

        return alert.severity === STATES.ERROR;
      });

      alertResponse.body = {
        health: states[Math.max.apply(null, health)],
        count: alerts.length
      };

      return alertResponse;
    }
  };

  return NotificationResource;
}
