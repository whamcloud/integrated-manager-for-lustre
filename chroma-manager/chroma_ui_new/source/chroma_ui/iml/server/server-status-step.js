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

  angular.module('server')
    .controller('ServerStatusStepCtrl', ['$scope', '$stepInstance', 'OVERRIDE_BUTTON_TYPES', 'data', 'statusSpark',
      'hostlistFilter',
      function ServerStatusStepCtrl ($scope, $stepInstance, OVERRIDE_BUTTON_TYPES, data, statusSpark, hostlistFilter) {
        _.extend(this, {
          pdsh: data.pdsh,
          /**
           * Update hostnames.
           * @param {String} pdsh
           * @param {Array} hostnames
           * @param {Object} hostnamesHash
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames, hostnamesHash) {
            this.serversStatus = hostlistFilter
              .setHash(hostnamesHash)
              .compute();
          },
          /**
           * tells manager to perform a transition.
           * @param {String} action
           */
          transition: function transition (action) {
            if (action === OVERRIDE_BUTTON_TYPES.OVERRIDE)
              return;

            statusSpark.end();

            $stepInstance.transition(action, {
              data: data,
              showCommand: action === OVERRIDE_BUTTON_TYPES.PROCEED
            });
          },
          /**
           * Close the modal
           */
          close: function close () {
            $scope.$emit('addServerModal::closeModal');
          }
        });

        var serverStatusStep = this;

        statusSpark.onValue('pipeline', function assignToScope (response) {
          serverStatusStep.isValid = response.body.valid;
          serverStatusStep.serversStatus = hostlistFilter
            .setHosts(response.body.objects)
            .compute();
        });
      }])
      .factory('serverStatusStep', [function serverStatusStepFactory () {
        return {
          templateUrl: 'iml/server/assets/html/server-status-step.html',
          controller: 'ServerStatusStepCtrl as serverStatus',
          onEnter: ['data', 'getTestHostSparkThen', 'serversToApiObjects',
            function onEnter (data, getTestHostSparkThen, serversToApiObjects) {
              var objects = serversToApiObjects(data.servers);

              return {
                statusSpark: getTestHostSparkThen(data.flint, { objects: objects }),
                data: data
              };
            }
          ],
          /**
           * Move to another step in the flow
           * @param {Object} steps
           * @param {String} action
           * @returns {Object} The step to move to.
           */
          transition: function transition (steps, action) {
            return (action === 'previous' ? steps.addServersStep : steps.selectServerProfileStep);
          }
        };
      }]);
}());
