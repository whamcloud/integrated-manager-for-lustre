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


angular.module('command')
  .controller('CommandModalCtrl', ['$scope', '$modalInstance', 'commands',
    function CommandModalCtrl ($scope, $modalInstance, commands) {
      'use strict';

      $scope.commandModal = {
        accordion0: true,
        /**
         * Closes the modal
         */
        close: function close () {
          $modalInstance.close('close');
        }
      };

      /**
       * @param {Object} response
       * Set the response on the scope.
       */
      commands.onValue('pipeline', function onValue (response) {
        $scope.commandModal.commands = response.body.objects;
      });
    }])
  .factory('openCommandModal', ['$modal', function openCommandModalFactory ($modal) {
    'use strict';

    return function openCommandModal (spark) {

      return $modal.open({
        templateUrl: 'iml/command/assets/html/command-modal.html',
        controller: 'CommandModalCtrl',
        windowClass: 'command-modal',
        backdropClass: 'command-modal-backdrop',
        resolve: {
          /**
           * Resolves a spark representing the set of provided commands
           * @returns {Object}
           */
          commands: [function getCommand () {
            return spark;
          }]
        }
      });
    };
  }])
  .factory('commandTransform', ['arrayOrItem', 'throwIfError', 'COMMAND_STATES',
    function commandTransformFactory (arrayOrItem, throwIfError, COMMAND_STATES) {
      'use strict';

      var findId = /\/(\d+)\/$/;

      /**
       * Given a collection, transforms it's parts.
       * @param {Object} response
       * @returns {Object}
       */
      return throwIfError(function commandTransform (response) {
        if ('error' in response)
          throw response.error;

        return arrayOrItem(function transform (command) {
          command.logs = command.logs.trim();

          if (command.cancelled)
            command.state = COMMAND_STATES.CANCELLED;
          else if (command.errored)
            command.state = COMMAND_STATES.FAILED;
          else if (command.complete)
            command.state = COMMAND_STATES.SUCCEEDED;
          else
            command.state = COMMAND_STATES.PENDING;

          command.jobIds = command.jobs.map(function getId (job) {
            return findId.exec(job)[1];
          });

          return command;
        }, response);
      });
    }
  ]);
