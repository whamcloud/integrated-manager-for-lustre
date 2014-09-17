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
    .controller('AddServerStepCtrl', ['$scope', '$stepInstance', 'buildTestHostData', 'data',
      function AddServerStepCtrl ($scope, $stepInstance, buildTestHostData, data) {
        var server = data.server;
        var fields = _.extend({
          sshAuthChoice: (server && server.install_method ? server.install_method : CHOICES.EXISTING_KEYS),
          pdsh: (server ? server.address : null)
        }, $stepInstance.getState());

        $scope.addServer = {
          fields: fields,
          CHOICES: CHOICES,
          /**
           * Called on pdsh view change.
           * @param {String} pdsh
           * @param {Array} hostnames
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames) {
            $scope.addServer.fields.pdsh = pdsh;

            if (hostnames != null)
              $scope.addServer.fields.address = hostnames;
          },
          /**
           * Call the transition.
           */
          transition: function transition () {
            $scope.addServer.disabled = true;

            data.serverData = buildTestHostData($scope.addServer.fields);

            $stepInstance.setState($scope.addServer.fields);

            $stepInstance.transition('next', { data: data });
          }
        };
      }
    ])
    .factory('buildTestHostData', [function buildTestHostDataFactory () {
      /**
       * Munges fields into an API acceptable format.
       * @param {Object} fields
       * @returns {Object}
       */
      return function buildTestHostData (fields) {
        var data = {
          address: fields.address,
          auth_type: fields.sshAuthChoice,
          commit: true
        };

        if (fields.sshAuthChoice === CHOICES.ROOT_PASSWORD) {
          _.extend(data, {
            root_password: fields.rootPassword
          });
        } else if (fields.sshAuthChoice === CHOICES.ANOTHER_KEY) {
          var pass = (fields.privateKeyPassphrase ? { private_key_passphrase: fields.privateKeyPassphrase } : {});

          _.extend(data, {
            private_key: fields.privateKey
          }, pass);
        }

        return data;
      };
    }])
    .factory('addServersStep', [function addServersStepFactory () {
      return {
        templateUrl: 'iml/server/assets/html/add-server-step.html',
        controller: 'AddServerStepCtrl',
        transition: ['$q', '$transition', 'data', 'testHost', 'throwIfError',
          function transition ($q, $transition, data, testHost, throwIfError) {
            var deferred = $q.defer();
            var statusSparkDeferred = $q.defer();
            var statusSpark = testHost(data.flint, data.serverData);

            data.statusSpark = statusSparkDeferred.promise;

            statusSpark.onValue('pipeline', throwIfError(function runOnce (response) {
              this.off();

              if (_.compact(response.body.errors).length)
                throw new Error(JSON.stringify(response.body.errors));

              statusSparkDeferred.resolve(statusSpark);

              deferred.resolve({
                step: $transition.steps.serverStatusStep,
                resolve: { data: data }
              });
            }));

            return deferred.promise;
          }
        ]
      };
    }]);
}());
