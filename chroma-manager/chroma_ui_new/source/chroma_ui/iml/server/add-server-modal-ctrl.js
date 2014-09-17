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
    .controller('AddServerModalCtrl', ['$scope', '$modalInstance', 'stepsManager', 'addServersStep',
      'serverStatusStep', 'selectServerProfileStep', 'server', 'regenerator', 'requestSocket',
      function AddServerModalCtrl ($scope, $modalInstance, stepsManager, addServersStep,
                                   serverStatusStep, selectServerProfileStep, server, regenerator, requestSocket) {

        var flint = regenerator(function setup () {
          return requestSocket();
        }, function teardown (spark) {
          spark.end();
        });

        var manager = stepsManager()
          .addStep('addServersStep', addServersStep)
          .addStep('serverStatusStep', serverStatusStep)
          .addStep('selectServerProfileStep', selectServerProfileStep)
          .start('addServersStep', {
            data: {
              server: server,
              flint: flint
            }
          });

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
      }
    ])
    .factory('openAddServerModal', ['$modal', function openAddServerModalFactory ($modal) {

      /**
       * Opens the add server modal
       * @param {Object} [server]
       * @returns {Object}
       */
      return function openAddServerModal (server) {
        return $modal.open({
          templateUrl: 'iml/server/assets/html/add-server-modal.html',
          controller: 'AddServerModalCtrl',
          windowClass: 'add-server-modal',
          resolve: {
            server: function getServer () {
              return server;
            }
          }
        });
      };
    }])
    .factory('createHosts', ['$q', 'requestSocket',
      function createHostsFactory ($q, requestSocket) {
        return function createHosts (serverData) {
          var spark = requestSocket();

          var objects = serverData.address.reduce(function buildObjects (arr, address) {
            arr.push(_(serverData).omit('address').extend({ address: address }).value());

            return arr;
          }, []);

          return spark.sendPost('/host', {
            json: { objects: objects }
          }, true)
            .catch(function throwError (response) {
              throw response.error;
            })
            .finally(function endSpark () {
              spark.end();
            });
        };
      }
    ])
    .factory('hostProfile', [function hostProfileFactory () {
      return function hostProfile (flint, hosts) {
        var spark = flint('hostProfile');

        spark.sendGet('/host_profile', {
          qs: {
            id__in: _.pluck(hosts, 'id')
          }
        });

        return spark;
      };
    }])
    .factory('testHost', ['throwIfError', function testHostFactory (throwIfError) {

      /**
       * Tests host with provided data.
       * @param {Function} flint
       * @param {Object} data
       * @returns {Object}
       */
      return function testHost (flint, data) {
        var spark = flint('testHost');

        spark.sendPost('/test_host', {
          json: data
        });

        spark.addPipe(throwIfError(function transformStatus (response) {
          var isValid = true;
          response.body.objects.forEach(function (status) {
              status.fields = Object.keys(status).reduce(function (obj, key) {
                if (key === 'address')
                  return obj;

                obj[_.capitalize(key.split('_').join(' '))] = status[key];

                return obj;
              }, {});

              status.invalid = _.contains(status, false);
              isValid = isValid && !status.invalid;
            });

          response.body.isValid = isValid;
          return response;
        }));

        return spark;
      };
    }])
    .factory('regenerator', [function regeneratorFactory () {
      return function regenerator (setup, teardown) {
        var cache = {};

        var getter = function get (key) {
          if (cache[key]) {
            teardown(cache[key]);
            delete cache[key];
          }

          return (cache[key] = setup());
        };

        getter.destroy = function destroy () {
          Object.keys(cache).forEach(function (key) {
            teardown(cache[key]);
          });

          cache = setup = teardown = null;
        };

        return getter;
      };
    }]);
}());
