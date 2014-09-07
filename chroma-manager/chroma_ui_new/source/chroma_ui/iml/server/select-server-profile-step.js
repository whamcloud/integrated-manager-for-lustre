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
    .controller('SelectServerProfileStepCtrl', ['$scope', '$stepInstance', 'data',
      function SelectServerProfileStepCtrl ($scope, $stepInstance, data) {
        $scope.selectServerProfile = {
          /**
           * Tells manager to perform a transition.
           * @param {String} action
           */
          transition: function transition (action) {
            $scope.selectServerProfile.disabled = true;

            off();

            $stepInstance.transition(action, {
              data: data,
              hostProfileData: $scope.selectServerProfile.data,
              profile: $scope.selectServerProfile.item
            });
          },
          onSelected: function onSelected (item) {
            $scope.selectServerProfile.warning = false;
            $scope.selectServerProfile.item = item;
            $scope.selectServerProfile.items = $scope.selectServerProfile.data.map(function (object) {
              return _.extend({}, object, {
                profile: item.caption,
                items: object.profiles[item.id],
                valid: object.profiles[item.id].length === 0
              });
            });
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
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames) {
            $scope.selectServerProfile.pdsh = pdsh;

            if (hostnames)
              $scope.selectServerProfile.hostnames = hostnames;
          },
          /**
           * Marks that we should show a warning.
           */
          showWarning: function showWarning () {
            $scope.selectServerProfile.warning = true;
          }
        };

        var off = data.hostProfileSpark.onValue('data', function (response) {
          var profiles = _.pluck(response.body.objects, 'profiles');

          var valid = buildReducer(function predicate (profile) {
            return profile.length === 0;
          })(profiles);

          var invalid = buildReducer(function predicate (profile) {
            return profile.length > 0;
          })(profiles);

          valid = _.difference(valid, invalid);

          $scope.selectServerProfile.data = response.body.objects;
          $scope.selectServerProfile.options = makeFancy(invalid).concat(makeFancy(valid, true));

          function makeFancy (profiles, valid) {
            return profiles.map(function (profile) {
              var option = {
                id: profile,
                caption: _.capitalize(profile.split('_').join(' ')),
                valid: valid
              };

              if (!valid)
                _.extend(option, {
                  labelType: 'label-danger',
                  label: 'Incompatible'
                });

              return option;
            });
          }

          function buildReducer (predicate) {
            return function reducer (profiles) {
              return _.unique(profiles.reduce(function (arr, profile) {
                return arr.concat(Object.keys(profile).filter(function (key) {
                  return predicate(profile[key]);
                }));
              }, []));
            };
          }
        });
      }])
    .factory('selectServerProfileStep', [function selectServerProfileStep () {
      return {
        templateUrl: 'iml/server/assets/html/select-server-profile-step.html',
        controller: 'SelectServerProfileStepCtrl',
        transition: ['$q', '$transition', 'data', 'requestSocket', 'hostProfileData', 'profile',
          function transition ($q, $transition, data, requestSocket, hostProfileData, profile) {
            if ($transition.action === 'end') {
              var spark = requestSocket();

              spark.sendPost('/host_profile', {
                json: {
                  objects: hostProfileData.map(function convertToObjects (data) {
                    return {
                      host: data.host,
                      profile: profile.id
                    };
                  })
                }
              }, true)
                .then($transition.end)
                .finally(function snuffSpark () {
                  spark.end();
                });

              return;
            }

            var deferred = $q.defer();

            data.statusSpark.onValue('pipeline', function onValue (response) {
              this.off();

              if (_.compact(response.body.errors).length)
                throw new Error(JSON.stringify(response.body.errors));

              var step;

              if ($transition.action === 'previous')
                step = response.body.isValid ? $transition.steps.addServersStep :
                  $transition.steps.serverStatusStep;

              deferred.resolve({
                step: step,
                resolve: { data: data }
              });
            });

            return deferred.promise;
          }
        ]
      };
    }]);
}());
