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


angular.module('server').controller('ConfirmServerActionModalCtrl',
  ['$scope', '$modalInstance', 'hosts', 'action', 'requestSocket',
  function ConfirmServerActionModalCtrl ($scope, $modalInstance, hosts, action, requestSocket) {
    'use strict';

    $scope.confirmServerActionModal = {
      hosts: hosts,
      actionName: action.value,
      inProgress: false,
      /**
       * Resolves the modal.
       * @param {Boolean} skips
       */
      go: function go (skips) {
        this.inProgress = true;

        var spark = requestSocket();
        spark.sendPost('/command', {
          json: {
            message: action.message,
            jobs: action.convertToJob(hosts)
          }
        }, ack);

        /**
         * Handles the response.
         * Closes the modal and might pass data.
         * @param {Object} response
         */
        function ack (response) {
          spark.end();

          if ('error' in response)
            throw response.error;

          var data;

          if (!skips)
            data = response.body;

          $modalInstance.close(data);
        }
      },
      /**
       * Rejects the modal.
       */
      cancel: function cancel () {
        $modalInstance.dismiss('cancel');
      }
    };
  }]);
