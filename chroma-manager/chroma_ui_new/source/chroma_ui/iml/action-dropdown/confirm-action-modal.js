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


angular.module('action-dropdown-module')
  .controller('ConfirmActionModalCtrl', ['$scope', '$modalInstance', 'title', 'confirmPrompts',
    function ConfirmActionModalCtrl  ($scope, $modalInstance, title, confirmPrompts) {
      'use strict';

      $scope.confirmAction = {
        title: title,
        confirmPrompts: confirmPrompts,
        /**
         * Closes the modal, passing a skip boolean.
         * @param {Boolean} skip
         */
        confirm: function onConfirm (skip) {
          $modalInstance.close(skip);
        },
        /**
         * Dismisses the modal.
         */
        cancel: function onCancel () {
          $modalInstance.dismiss('cancel');
        }
      };
    }])
  .factory('openConfirmActionModal', ['$modal', function openConfirmActionModalFactory ($modal) {
    'use strict';

    return function openConfirmActionModal (title, confirmPrompts) {
      return $modal.open({
        templateUrl: 'iml/action-dropdown/assets/html/confirm-action-modal.html',
        controller: 'ConfirmActionModalCtrl',
        windowClass: 'confirm-action-modal',
        backdropClass: 'confirm-action-modal-backdrop',
        backdrop: 'static',
        resolve: {
          /**
           * Get the title.
           * @returns {String}
           */
          title: function getTitle () {
            return title;
          },
          /**
           * Get the confirm prompts.
           * @returns {Array}
           */
          confirmPrompts: function getConfirmPrompts () {
            return confirmPrompts;
          }
        }
      });
    };
  }]);
