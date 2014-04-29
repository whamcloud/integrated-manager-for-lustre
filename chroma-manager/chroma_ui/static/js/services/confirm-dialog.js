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


(function (_) {
  'use strict';

  angular.module('services').factory('confirmDialog', ['$dialog', '$q', 'STATIC_URL', factory]);

  function factory($dialog, $q, STATIC_URL) {

    return {
      /**
       * @description method to setup and return a dialog
       * @param {object} customOptions Options this dialog
       * @param {object} customOptions.dialog options to be passed to $dialog
       * @param {object} customOptions.content options that populate the dialog template
       * @param {string} [customOptions.content.title=Confirm] Title of the dialog
       * @param {string} [customOptions.content.message=Confirm this action?] Main content for the confirmation dialog
       * @param {string} [customOptions.content.confirmText=Confirm] Text of the affirmative button
       * @param {string} [customOptions.content.cancelText=Cancel] Text of the negative button
       */
      setup: function(customOptions) {
        var options = {
          // see bootstrap-ui $dialog options
          dialog: {
            dialogFade: true,
            backdropClick: false,
            templateUrl: '%spartials/dialogs/confirm-dialog.html'.sprintf(STATIC_URL),
            controller: function($scope, dialog) {
              options.content.cancelAction = function() { dialog.close('cancel'); };
              options.content.confirmAction = function() { dialog.close('confirm'); };
              $scope.confirmDialog = options.content;
            }
          },
          content: {
            title: 'Confirm',
            message: 'Confirm this action?',
            confirmText: 'Confirm',
            cancelText: 'Cancel',
          }
        };

        _.merge(options, customOptions || {});

        var dialog = $dialog.dialog(options.dialog);
        var oldOpen = dialog.open;
        dialog.open = function() {
          return oldOpen.apply(dialog, arguments).then(function (status) {
            return (status === 'confirm') ? status : $q.reject(status);
          });
        };
        return dialog;
      }
    };
  }


}(window.lodash));
