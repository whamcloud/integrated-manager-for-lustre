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

  var CHOICES = Object.freeze({
    EXISTING_KEYS: 'existing_keys_choice',
    ROOT_PASSWORD: 'id_password_root',
    ANOTHER_KEY: 'private_key_choice'
  });

  angular.module('server')
    .constant('ADD_SERVER_AUTH_CHOICES', CHOICES)
    .controller('AddServerStepCtrl', ['$scope', '$stepInstance', 'data',
      function AddServerStepCtrl ($scope, $stepInstance, data) {
        var server = data.server;

        $scope.addServer = {
          fields: _.extend({ auth_type: CHOICES.EXISTING_KEYS }, server, {
            pdsh: (server && (server.pdsh || server.address[0]) || null)
          }),
          CHOICES: CHOICES,
          /**
           * Called on pdsh view change.
           * @param {String} pdsh
           * @param {Array} hostnames
           * @param {Object} hostnamesHash
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames, hostnamesHash) {
            $scope.addServer.fields.pdsh = pdsh;

            if (hostnames != null) {
              $scope.addServer.fields.address = hostnames;
              $scope.addServer.fields.addressHash = hostnamesHash;
            }
          },
          /**
           * Call the transition.
           */
          transition: function transition () {
            $scope.addServer.disabled = true;

            data.server = _.extend({}, server, $scope.addServer.fields);

            $stepInstance.transition('next', { data: data });
          },
          /**
           * Close the modal
           */
          close: function close () {
            $scope.$emit('closeModal');
          }
        };
      }
    ])
    .factory('addServersStep', [function addServersStepFactory () {
      return {
        templateUrl: 'iml/server/assets/html/add-server-step.html',
        controller: 'AddServerStepCtrl',
        transition: ['$transition', 'data', 'getTestHostSparkThen',
          function transition ($transition, data, getTestHostSparkThen) {
            data.statusSpark = getTestHostSparkThen(data.flint, data.server);

            return {
              step: $transition.steps.serverStatusStep,
              resolve: { data: data }
            };
          }
        ]
      };
    }]);
}());
