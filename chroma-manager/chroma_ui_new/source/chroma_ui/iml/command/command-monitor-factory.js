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
  .controller('CommandMonitorCtrl', ['$scope', 'commandMonitor', 'openCommandModal', 'createCommandSpark',
    function CommandMonitorCtrl ($scope, commandMonitor, openCommandModal, createCommandSpark) {
      'use strict';

      /**
       * Ends the spark when the scope is destroyed.
       */
      $scope.$on('$destroy', function onDestroy () {
        commandMonitor.end();
      });

      $scope.commandMonitor = {
        /**
         * Opens the command modal with pending data.
         */
        showPending: function showPending () {
          var spark = createCommandSpark(this.lastResponse);
          openCommandModal(spark)
            .result.then(function endSpark () {
              spark.end();
            });
        }
      };

      commandMonitor.onValue('pipeline', function updateMonitor (response) {
        $scope.commandMonitor.pending = response.body.objects.length;
        $scope.commandMonitor.lastResponse = response;
      });
    }])
  .factory('commandMonitor', ['requestSocket', 'throwIfError',
    function commandMonitorFactory (requestSocket, throwIfError) {
      'use strict';

      var spark = requestSocket();

      spark.sendGet('/command', {
        qs: {
          limit: 0,
          errored: false,
          complete: false
        }
      });

      /**
       * Filters out cancelled commands since the API doesn't.
       * @param {Object} response
       */
      spark.addPipe(throwIfError(function filterCancelled (response) {
        response.body.objects = response.body.objects.filter(function removeCancelled (command) {
          return command.cancelled === false;
        });

        return response;
      }));

      return spark;
    }
  ]);
