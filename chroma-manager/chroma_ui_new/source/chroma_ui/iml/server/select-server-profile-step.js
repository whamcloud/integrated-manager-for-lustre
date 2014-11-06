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
    .controller('SelectServerProfileStepCtrl', ['$scope', '$stepInstance', 'OVERRIDE_BUTTON_TYPES',
      'CACHE_INITIAL_DATA', 'data',
      function SelectServerProfileStepCtrl ($scope, $stepInstance, OVERRIDE_BUTTON_TYPES,
                                            CACHE_INITIAL_DATA, data) {
        $scope.selectServerProfile = {
          pdsh: ((data.server && data.server.pdsh) || null),
          /**
           * Tells manager to perform a transition.
           * @param {String} action
           */
          transition: function transition (action) {
            if (action === OVERRIDE_BUTTON_TYPES.OVERRIDE)
              return;

            off();

            $stepInstance.transition(action, {
              data: data,
              hostProfileData: $scope.selectServerProfile.data,
              profile: $scope.selectServerProfile.profile
            });
          },
          /**
           * Called when the user selects a new server profile.
           * @param {Object} profile The selected profile
           */
          onSelected: function onSelected (profile) {
            $scope.selectServerProfile.overridden = false;
            $scope.selectServerProfile.profile = profile;
          },
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
           * @param {Array|undefined} hostnames
           * @param {Object} hostnamesHash
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames, hostnamesHash) {
            $scope.selectServerProfile.pdsh = pdsh;

            if (hostnames) {
              $scope.selectServerProfile.hostnames = hostnames;
              $scope.selectServerProfile.hostnamesHash = hostnamesHash;
            }
          },
          /**
           * Close the modal
           */
          close: function close () {
            $scope.$emit('addServerModal::closeModal');
          }
        };

        var off = data.hostProfileSpark.onValue('data', function handleData (response) {
          //Save initial data for transition.
          $scope.selectServerProfile.data = response.body.objects;

          // Pull out the profiles and flatten them.
          var profiles = [{}]
            .concat(_.pluck(response.body.objects, 'profiles'))
            .concat(function concatArrays (a, b) {
              return _.isArray(a) ? a.concat(b) : undefined;
            });
          var merged = _.merge.apply(_, profiles);

          // Mutate the structure to something that is usable
          // by both the select box and the christmas tree.
          $scope.selectServerProfile.profiles = Object.keys(merged).reduce(function buildStructure (arr, profileName) {
            var item = {
              name: profileName,
              uiName: _.find(CACHE_INITIAL_DATA.server_profile, { name: profileName }).ui_name,
              invalid: merged[profileName].some(didProfileFail)
            };

            item.hosts = response.body.objects.map(function setHosts (host) {
              var profiles = host.profiles[profileName];

              return {
                address: host.address,
                invalid: profiles.some(didProfileFail),
                problems: profiles,
                uiName: item.uiName
              };
            });

            arr.push(item);

            return arr;
          }, []);

          // Avoid a stale reference here by
          // pulling off the new value if we already have a profile.
          var profile = $scope.selectServerProfile.profile;
          $scope.selectServerProfile.profile = (profile ?
            _.find($scope.selectServerProfile.profiles, { name: profile.name }) :
            $scope.selectServerProfile.profiles[0]
          );
        });

        /**
         * Predicate. Did the given profile fail it's checks.
         * @param {Object} profile The profile to check.
         * @returns {boolean}
         */
        function didProfileFail (profile) {
          return !profile.pass;
        }
      }])
    .factory('selectServerProfileStep', [
      function selectServerProfileStep () {
        return {
          templateUrl: 'iml/server/assets/html/select-server-profile-step.html',
          controller: 'SelectServerProfileStepCtrl',
          transition: ['$transition', 'data', 'requestSocket', 'hostProfileData', 'profile', '$q',
            'waitForCommandCompletion', 'OVERRIDE_BUTTON_TYPES',
            function transition ($transition, data, requestSocket, hostProfileData, profile, $q,
                                 waitForCommandCompletion, OVERRIDE_BUTTON_TYPES) {
              if ($transition.action === 'previous')
                return {
                  step: $transition.steps.serverStatusStep,
                  resolve: { data: data }
                };

              var spark = requestSocket();

              data.serverSpark.onceValue('data', function sendNewProfiles (response) {
                var servers = response.body.objects;

                var objects = hostProfileData
                  .map(function convertToObjects (data) {
                    return {
                      host: data.host,
                      profile: profile.name
                    };
                  })
                  .filter(function limitToUnconfigured (object) {
                    var server = _.find(servers, { id: object.host.toString()});

                    return server && server.server_profile && server.server_profile.initial_state === 'unconfigured';
                  });

                var promise;
                if (objects.length > 0) {
                  promise = spark.sendPost('/host_profile', {
                    json: { objects: objects }
                  }, true)
                    .then(function transformResponse (response) {
                      return {
                        body: {
                          objects: response.body.commands.map(function mapCommands (currentCommand) {
                            return {command: currentCommand};
                          })
                        }
                      };
                    })
                    .then(waitForCommandCompletion($transition.action === OVERRIDE_BUTTON_TYPES.PROCEED))
                    .catch(function throwError (response) {
                      throw response.error;
                    });
                } else {
                  promise = $q.when();
                }

                promise.then($transition.end)
                  .finally(function snuffSpark () {
                    spark.end();
                  });
              });

            }
          ]
        };
      }
    ]);
}());
