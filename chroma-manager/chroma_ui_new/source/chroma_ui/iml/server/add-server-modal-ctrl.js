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
    .constant('ADD_SERVER_STEPS', Object.freeze({
      ADD: 'addServersStep',
      STATUS: 'serverStatusStep',
      SELECT_PROFILE: 'selectServerProfileStep'
    }))
    .factory('addServerSteps', ['ADD_SERVER_STEPS', 'addServersStep', 'serverStatusStep', 'selectServerProfileStep',
      function addServerStepsFactory (ADD_SERVER_STEPS, addServersStep, serverStatusStep, selectServerProfileStep) {
        var steps = {};
        steps[ADD_SERVER_STEPS.ADD] = addServersStep;
        steps[ADD_SERVER_STEPS.STATUS] = serverStatusStep;
        steps[ADD_SERVER_STEPS.SELECT_PROFILE] = selectServerProfileStep;

        return steps;
      }
    ])
    .controller('AddServerModalCtrl', ['$scope', '$modalInstance', 'ADD_SERVER_STEPS', 'stepsManager',
      'serverSpark', 'server', 'step', 'getFlint', 'getTestHostSparkThen', 'addServerSteps', 'waitUntilLoadedStep',
      'createOrUpdateHostsThen', 'hostProfile',
      function AddServerModalCtrl ($scope, $modalInstance, ADD_SERVER_STEPS, stepsManager,
                                   serverSpark, server, step, getFlint, getTestHostSparkThen, addServerSteps,
                                   waitUntilLoadedStep, createOrUpdateHostsThen, hostProfile) {

        var manager = stepsManager();

        _.pairs(addServerSteps)
          .forEach(function addStep (pair) {
            manager.addStep(pair[0], pair[1]);
          });

        manager.addWaitingStep(waitUntilLoadedStep);

        var flint = getFlint();

        if (server)
          server = _.extend({}, server, {
            address: [server.address],
            auth_type: server.install_method
          });

        var resolves = {
          data: {
            serverSpark: serverSpark,
            server: server,
            flint: flint
          }
        };

        if (!step)
          step = ADD_SERVER_STEPS.ADD;

        if (step !== ADD_SERVER_STEPS.ADD)
          resolves.data.statusSpark = getTestHostSparkThen(flint, server);

        if (step === ADD_SERVER_STEPS.SELECT_PROFILE)
          resolves.data.hostProfileSpark = createOrUpdateHostsThen(server, serverSpark)
            .then(function getHostProfileSpark (response) {
              var hosts = _.pluck(response.body.objects, 'host');
              var hostSpark = hostProfile(flint, hosts);

              return hostSpark.onceValueThen('data')
                .then(function () {
                  return hostSpark;
                });
            });

        manager.start(step, resolves);

        manager.result.end.then(function closeModal () {
          $modalInstance.close();
        });

        $scope.addServer = {
          manager: manager
        };

        $scope.$on('$destroy', function () {
          manager.destroy();
          flint.destroy();
        });

        // Listen of the closeModal event from the step controllers
        $scope.$on('addServerModal::closeModal', function onClose() {
          $modalInstance.close();
        });
      }
    ])
    .factory('openAddServerModal', ['$modal', function openAddServerModalFactory ($modal) {

      /**
       * Opens the add server modal
       * @param {Object} serverSpark
       * @param {Object} [server]
       * @param {Object} [step]
       * @returns {Object}
       */
      return function openAddServerModal (serverSpark, server, step) {
        return $modal.open({
          templateUrl: 'iml/server/assets/html/add-server-modal.html',
          controller: 'AddServerModalCtrl',
          backdropClass: 'add-server-modal-backdrop',
          backdrop: 'static',
          keyboard: 'false',
          windowClass: 'add-server-modal',
          resolve: {
            serverSpark: function getServerSpark () {
              return serverSpark;
            },
            server: function getServer () {
              return server;
            },
            step: function getStep () {
              return step;
            }
          }
        });
      };
    }])
    .factory('hostProfile', [function hostProfileFactory () {
      return function hostProfile (flint, hosts) {
        var spark = flint('hostProfile');

        spark.sendGet('/host_profile', {
          qs: {
            id__in: _.pluck(hosts, 'id'),
            limit: 0
          }
        });

        return spark;
      };
    }])
    .factory('getTestHostSparkThen', ['ADD_SERVER_AUTH_CHOICES', 'throwIfServerErrors',
      'throwResponseError', 'throwIfError',
      function getTestHostSparkThenFactory (ADD_SERVER_AUTH_CHOICES, throwIfServerErrors,
                                            throwResponseError, throwIfError) {

        /**
         * Tests host with provided data.
         * Keeps asking about the server's status.
         * Returns a promise containing the spark.
         * @param {Function} flint Creates sparks.
         * @param {Object} data The data to send.
         * @returns {Object} A promise
         */
        return function getTestHostSparkThen (flint, data) {
          var toPick = ['address', 'auth_type'];

          if (data.auth_type === ADD_SERVER_AUTH_CHOICES.ROOT_PASSWORD) {
            toPick.push('root_password');
          } else if (data.auth_type === ADD_SERVER_AUTH_CHOICES.ANOTHER_KEY) {
            toPick.push('private_key');

            if (data.private_key_passphrase)
              toPick.push('private_key_passphrase');
          }

          var spark = flint('testHost');

          spark.sendPost('/test_host', {
            json: _.pick(data, toPick)
          });

          return spark.addPipe(throwIfError(throwIfServerErrors(function transformStatus (response) {
            var isValid = true;
            response.body.objects.forEach(function addProperties (status) {
              status.fields = Object.keys(status).reduce(function (obj, key) {
                if (key !== 'address')
                  obj[_.capitalize(key.split('_').join(' '))] = status[key];

                return obj;
              }, {});

              status.invalid = _.contains(status, false) || _.contains(status, null);

              isValid = isValid && !status.invalid;
            });

            response.body.isValid = isValid;
            return response;
          })))
          .onceValueThen('pipeline')
            .catch(throwResponseError)
            .then(function resolveWithSpark () {
              return spark;
            });
        };
      }
    ])
    .factory('throwIfServerErrors', [function throwIfServerErrorsFactory () {
      /**
       * HOF. Will throw if a bulk server response has errors
       * or call the fn with the response.
       * @param {Function} fn
       * @returns {Function}
       */
      return function throwIfServerErrors (fn) {
        return function throwOrCall (response) {
          if (response.body && _.compact(response.body.errors).length)
            throw new Error(JSON.stringify(response.body.errors));

          return fn(response);
        };
      };
    }]);
}());
