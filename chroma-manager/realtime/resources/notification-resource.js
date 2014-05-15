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

var inherits = require('util').inherits,
  STATES,
  _ = require('lodash');

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

function notificationResourceFactory (Resource, AlertResource, CommandResource, EventResource, Q) {
  var commandResource = new CommandResource();
  var alertResource = new AlertResource();
  var eventResource = new EventResource();

  /**
   * Extension of the Resource.
   * Used for joining alerts, commands and events to create a status.
   * @constructor
   */

  function NotificationResource() {
    Resource.call(this, 'notification');
  }

  inherits(NotificationResource, Resource);


  /**
   * Gets alerts, events and commands and joins them.
   * @param {Object} params
   */
  NotificationResource.prototype.httpGetHealth = function httpGetHealth (params) {
    return Q.all([
      alertResource.httpGetList(
        mergeParams({qs: {active: true, severity__in: [STATES.WARN, STATES.ERROR], limit: 0}})
      ),
      alertResource.httpGetList(
        mergeParams({qs: {active: false, dismissed: false, severity__in: STATES.WARN, limit: 1}})
      ),
      eventResource.httpGetList(
        mergeParams({qs: {dismissed: false, severity__in: [STATES.WARN, STATES.ERROR], limit: 1}})
      ),
      commandResource.httpGetList(
        mergeParams({qs: {errored: true, dismissed: false, limit: 1}})
      )
    ]).spread(allDone);

    function mergeParams(getParams) {
      return _.merge({}, params, getParams);
    }

    function allDone(activeAlertResp, inactiveAlertResp, eventResp, commandResp) {
      var alerts = activeAlertResp.body.objects,
        inactiveAlerts = inactiveAlertResp.body.objects,
        events = eventResp.body.objects,
        commands = commandResp.body.objects;

      var states = [STATES.GOOD, STATES.WARN, STATES.ERROR];
      var health = [states.indexOf(STATES.GOOD)];

      //1 or more unacknowledged WARN or higher events: amber
      events.forEach(function () {
        health.push(states.indexOf(STATES.WARN));
      });

      //1 or more ERROR alerts are active: red else: 1 or more WARN alerts are active: amber
      alerts.some(function (alert) {
        health.push(states.indexOf(alert.severity));

        return alert.severity === STATES.ERROR;
      });

      // 1 or more WARN alerts are inactive but have not been dismissed: amber
      // 1 or more unacknowledged failed commands: amber
      [inactiveAlerts, commands].forEach(function (group) {
        if (group.length)
          health.push(states.indexOf(STATES.WARN));
      });

      health = _.unique(health);
      commandResp.body = states[Math.max.apply(null, health)];
      return commandResp;
    }
  };

  return NotificationResource;
}
