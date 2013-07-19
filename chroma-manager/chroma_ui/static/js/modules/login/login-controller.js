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

  function LoginCtrl($scope, $window, SessionModel, EULA_STATES, $dialog, HELP_TEXT, UI_ROOT) {

    /**
     * Initializes the eula dialog and opens it.
     * @param {UserModel} user
     * @returns {Object} A promise that is resolved when the dialog closes.
     */
    function initializeEulaDialog(user) {
      return $dialog.dialog({
        dialogFade: true,
        backdropClick: false,
        resolve: {
          doneCallback: function () {
            return doneCallback;
          },
          user: function () {
            return user;
          }
        }
      }).open($scope.config.asStatic('js/modules/login/assets/html/eula.html'), 'EulaCtrl');
    }

    /**
     * Initializes the denied dialog and opens it.
     * @returns {Object} A promise that is resolved when the dialog closes.
     */
    function initializeDeniedDialog() {
      return $dialog.dialog({
        dialogFade: true,
        backdropClick: false,
        resolve: {
          message: function () {
            return HELP_TEXT.access_denied_eula;
          }
        }
      }).open($scope.config.asStatic('partials/dialogs/access_denied.html'), 'AccessDeniedCtrl');
    }

    /**
     * After the login is submitted, this function decides whether to show the eula dialog, denied dialog or redirect.
     * @param {UserModel} user
     * @returns {Object|void} Returns a promise if a dialog is shown, otherwise undefined.
     */
    function nextStep(user) {
      var state = user.eula_state;

      if (state === EULA_STATES.EULA) {
        return initializeEulaDialog(user);
      } else if (state === EULA_STATES.DENIED) {
        return initializeDeniedDialog();
      } else if (state === EULA_STATES.PASS) {
        doneCallback();
      }
    }

    /**
     * Redirects the user to the base url.
     */
    function doneCallback() {
      $window.location.href = UI_ROOT;
    }

    $scope.login = {
      /**
       * Submits the login, calling nextStep if successful.
       */
      submitLogin: function submitLogin() {
        $scope.login.inProgress = true;

        $scope.login.loginThen = SessionModel.save({
          username: this.username,
          password: this.password
        }).$promise.then;

        function callback() {
          $scope.login.inProgress = false;
        }

        $scope.login.loginThen(function getSession() {
          return SessionModel.get().$promise;
        })
        .then(function (session) {
          return nextStep(session.user);
        })
        .then(callback, callback);
      }
    };
  }

  angular.module('login')
  .controller('LoginCtrl',
    ['$scope', '$window', 'SessionModel', 'user_EULA_STATES', '$dialog', 'HELP_TEXT', 'UI_ROOT', LoginCtrl]
  );
}());
