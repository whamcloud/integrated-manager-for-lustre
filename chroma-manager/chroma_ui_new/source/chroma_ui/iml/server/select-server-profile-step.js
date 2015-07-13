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
    .controller('SelectServerProfileStepCtrl', ['$scope', '$stepInstance', 'OVERRIDE_BUTTON_TYPES',
      'data', 'hostProfileSpark', 'createHostProfiles',
      function SelectServerProfileStepCtrl ($scope, $stepInstance, OVERRIDE_BUTTON_TYPES,
                                            data, hostProfileSpark, createHostProfiles) {
        _.extend(this, {
          pdsh: data.pdsh,
          /**
           * Tells manager to perform a transition.
           * @param {String} action
           */
          transition: function transition (action) {
            if (action === OVERRIDE_BUTTON_TYPES.OVERRIDE)
              return;

            this.disabled = true;

            hostProfileSpark.end();

            if (action === 'previous')
              return $stepInstance.transition(action, { data: data });

            createHostProfiles(data.serverSpark, this.profile, action === OVERRIDE_BUTTON_TYPES.PROCEED)
              .finally($stepInstance.end);
          },
          /**
           * Called when the user selects a new server profile.
           * @param {Object} profile The selected profile
           */
          onSelected: function onSelected (profile) {
            this.overridden = false;
            this.profile = profile;
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
           * @param {Array} hostnames
           * @param {Object} hostnamesHash
           */
          pdshUpdate: function pdshUpdate (pdsh, hostnames, hostnamesHash) {
            this.hostnamesHash = hostnamesHash;
          },
          /**
           * Close the modal
           */
          close: function close () {
            $scope.$emit('addServerModal::closeModal');
          }
        });

        var selectServerProfileStep = this;

        hostProfileSpark.onValue('pipeline', function (profiles) {
          selectServerProfileStep.profiles = profiles;

          // Avoid a stale reference here by
          // pulling off the new value if we already have a profile.
          var profile = selectServerProfileStep.profile;
          selectServerProfileStep.profile = (
            profile ?
            _.find(profiles, { name: profile.name }) :
            profiles[0]
          );
        });
      }])
    .factory('selectServerProfileStep', [
      function selectServerProfileStep () {
        return {
          templateUrl: 'iml/server/assets/html/select-server-profile-step.html',
          controller: 'SelectServerProfileStepCtrl as selectServerProfile',
          onEnter: ['data', 'createOrUpdateHostsThen', 'getHostProfiles', 'waitForCommandCompletion', 'showCommand',
            function onEnter (data, createOrUpdateHostsThen, getHostProfiles, waitForCommandCompletion, showCommand) {
              var hostsPromise = createOrUpdateHostsThen(data.servers, data.serverSpark);

              var hostProfilePromise = hostsPromise
                .then(_.unwrapResponse(_.fmapProp('command_and_host')))
                .then(waitForCommandCompletion(showCommand))
                .then(_.pluckPath('body.objects'))
                .then(_.fmapProp('host'))
                .then(function getHostProfileSpark (hosts) {
                  var hostProfileSpark = getHostProfiles(data.flint, hosts);

                  return hostProfileSpark.onceValueThen('data')
                    .then(function handleResponse () {
                      return hostProfileSpark;
                    });
                });

              return {
                data: data,
                hostProfileSpark: hostProfilePromise
              };
            }
          ],
          transition: function transition (steps) {
            return steps.serverStatusStep;
          }
        };
      }
    ]);
}());
