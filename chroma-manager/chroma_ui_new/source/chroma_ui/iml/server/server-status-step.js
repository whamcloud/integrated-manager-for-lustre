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
    .controller('ServerStatusStepCtrl', ['$scope', '$stepInstance', 'OVERRIDE_BUTTON_TYPES', 'data',
      'naturalSortFilter', 'pdshFilter',
      function ServerStatusStepCtrl ($scope, $stepInstance, OVERRIDE_BUTTON_TYPES, data, naturalSortFilter,
                                     pdshFilter) {

        var matchingSpaces = / /g;

        $scope.serverStatus = {
          pdsh: ((data.server && data.server.pdsh) || null),

          /**
           * Update hostnames.
           * @param {String} pdsh
           * @param {Array} hostnames
           * @param {Object} hostnamesHash
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames, hostnamesHash) {
            if (hostnames) {
              $scope.serverStatus.hostnames = hostnames;
              $scope.serverStatus.hostnamesHash = hostnamesHash;
            }
          },
          /**
           * tells manager to perform a transition.
           * @param {String} action
           */
          transition: function transition (action) {
            off();

            if (action !== OVERRIDE_BUTTON_TYPES.OVERRIDE)
              $stepInstance.transition(action, { data: data });
          },
          /**
           * Close the modal
           */
          close: function close () {
            $scope.$emit('addServerModal::closeModal');
          },
          /**
           * Convert the check to something that maps back to a help property
           * @param {String} key
           * @returns {string}
           */
          convertToHelp: function convertToHelp (key) {
            return key.toLowerCase().replace(matchingSpaces, '_');
          }
        };

        var off = data.statusSpark.onValue('pipeline', function assignToScope (response) {
          $scope.serverStatus.isValid = response.body.isValid;
          $scope.serverStatus.status = naturalSortFilter(
            pdshFilter(response.body.objects, $scope.serverStatus.hostnamesHash, comparator),
            comparator
          );

          /**
           * Defines the property to look at for host name comparison.
           * @param {Object} obj
           * @returns {String}
           */
          function comparator (obj) {
            return obj.address;
          }
        });
      }])
      .factory('serverStatusStep', ['OVERRIDE_BUTTON_TYPES', function serverStatusStepFactory (OVERRIDE_BUTTON_TYPES) {
        return {
          templateUrl: 'iml/server/assets/html/server-status-step.html',
          controller: 'ServerStatusStepCtrl',
          transition: ['$transition', 'data', 'createOrUpdateHostsThen', 'hostProfile', 'waitForCommandCompletion',
            function transition ($transition, data, createOrUpdateHostsThen, hostProfile, waitForCommandCompletion) {
              var step;

              if ($transition.action === 'previous') {
                step = $transition.steps.addServersStep;
              } else {
                step = $transition.steps.selectServerProfileStep;

                var hostsPromise = createOrUpdateHostsThen(data.server, data.serverSpark)
                  .then(waitForCommandCompletion($transition.action === OVERRIDE_BUTTON_TYPES.PROCEED))
                  .catch(function throwError (response) {
                    throw response.error;
                  });

                data.hostProfileSpark = hostsPromise.then(function getHostProfileSpark (response) {
                  var hosts = _.pluck(response.body.objects, 'host');
                  var hostSpark = hostProfile(data.flint, hosts);

                  return hostSpark.onceValueThen('data')
                    .then(function handleResponse () {
                      return hostSpark;
                    }, function handleError (response) {
                      throw response.error;
                    });
                });
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
