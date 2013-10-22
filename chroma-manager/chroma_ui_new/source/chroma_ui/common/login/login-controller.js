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

  function LoginCtrl($window, $modal, $q, SessionModel, HELP_TEXT, UI_ROOT) {
    /**
     * Initializes the eula modal and opens it.
     * @param {UserModel} user
     * @returns {Object} A promise that is resolved when the modal closes.
     */
    function initializeEulaDialog(user) {
      return $modal.open({
        templateUrl: 'common/login/assets/html/eula.html',
        controller: 'EulaCtrl',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          user: _.iterators.K(user)
        }
      }).result;
    }

    /**
     * Initializes the denied dialog and opens it.
     * @returns {Object} A promise that is resolved when the dialog closes.
     */
    var initializeDeniedDialog = function() {
      return $modal.open({
        templateUrl: 'common/access-denied/assets/html/access-denied.html',
        controller: 'AccessDeniedCtrl',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          message: _.iterators.K(HELP_TEXT.access_denied_eula)
        }
      }).result;
    }.bind(this);

    /**
     * Submits the login, calling nextStep if successful.
     */
    this.submitLogin = function submitLogin() {
      this.inProgress = true;

      var promise = SessionModel.login(this.username, this.password).$promise
      .then(function (session) {
        return session.user.actOnEulaState(initializeEulaDialog, initializeDeniedDialog);
      })
      .then(function () {
        $window.location.href = UI_ROOT;
      })
      .catch(function (reason) {
        if (reason === 'dismiss')
          return SessionModel.del().$promise;

        return $q.reject(reason);
      })
      .finally(function () {
        this.inProgress = false;
      }.bind(this));

      this.validate = { promise: promise };
    };
  }

  angular.module('login').controller('LoginCtrl',
    ['$window', '$modal', '$q', 'SessionModel', 'HELP_TEXT', 'UI_ROOT', LoginCtrl]
  );
}());
