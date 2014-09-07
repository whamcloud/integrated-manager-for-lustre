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

  angular.module('server')
    .controller('ServerStatusStepCtrl', ['$scope', '$stepInstance', 'data',
      function ServerStatusStepCtrl ($scope, $stepInstance, data) {
        $scope.serverStatus = {
          /**
           * Used by filters to determine the context.
           * @param {Object} item
           * @returns {String}
           */
          getHostPath: function getHostPath (item) {
            return item.address;
          },
          /**
           * Update hostnames.
           * @param {String} pdsh
           * @param {Array} hostnames
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames) {
            if (hostnames)
              $scope.serverStatus.hostnames = hostnames;
          },
          /**
           * Marks that we should show a warning.
           */
          showWarning: function showWarning () {
            $scope.serverStatus.warning = true;
          },
          /**
           * tells manager to perform a transition.
           * @param {String} action
           */
          transition: function transition (action) {
            $scope.serverStatus.disabled = true;

            off();

            $stepInstance.transition(action, { data: data });
          }
        };

        var off = data.statusSpark.onValue('pipeline', function assignToScope (response) {
          $scope.serverStatus.status = response.body.objects;
        });
      }])
      .factory('serverStatusStep', [function serverStatusStepFactory () {
        return {
          templateUrl: 'iml/server/assets/html/server-status-step.html',
          controller: 'ServerStatusStepCtrl',
          transition: ['$transition', 'data', 'createHosts',
            function transition ($transition, data, createHosts) {
              var step;

              if ($transition.action === 'previous') {
                step = $transition.steps.addServersStep;
              }  else if ($transition.action === 'next') {
                step = $transition.steps.selectServerProfileStep;
                data.hostProfileSpark = createHosts(data.flint, data.serverData);
              }

              return {
                step: step,
                resolve: { data: data }
              };
            }
          ]
        };
      }]);
}());
