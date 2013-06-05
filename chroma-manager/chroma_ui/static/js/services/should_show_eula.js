//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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

  function factory(SessionModel, $rootScope, $dialog, HELP_TEXT) {
    return function (credentials, doneCallback) {
      var session = SessionModel.get();

      session.$promise
        .then(function () {
          return session.$delete().$promise;
        })
        .then(callback);

      function initializeEulaDialog() {
        $dialog.dialog({
          dialogFade: true,
          backdropClick: false,
          resolve: {
            doneCallback: function () {
              return doneCallback;
            },
            credentials: function () {
              return credentials;
            }
          }
        }).open($rootScope.config.asStatic('partials/dialogs/eula.html'), 'EulaCtrl');
      }

      function initializeDeniedDialog() {
        $dialog.dialog({
          dialogFade: true,
          backdropClick: false,
          resolve: {
            message: function () {
              return HELP_TEXT.access_denied_eula;
            }
          }
        }).open($rootScope.config.asStatic('partials/dialogs/access_denied.html'), 'AccessDeniedCtrl');
      }

      function passThrough() {
        SessionModel.save(credentials).$promise.then(doneCallback);
      }

      function callback() {
        var user = session.user;

        (user.shouldShowEula() ? initializeEulaDialog :
          (user.is_superuser || user.accepted_eula ? passThrough: initializeDeniedDialog)
        )();
      }
    };
  }

  angular.module('services').factory('shouldShowEula', ['SessionModel', '$rootScope', '$dialog', 'HELP_TEXT', factory]);
}());


