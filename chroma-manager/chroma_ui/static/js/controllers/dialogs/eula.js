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

  function EulaCtrl(SessionModel, $scope, dialog, HELP_TEXT, credentials, doneCallback) {
    /**
     * Wrapper function that creates an action for EULA buttons.
     * @param {boolean} state
     * @param {Function} [afterUpdateCallback]
     * @returns {Function}
     */
    function createAction(state, afterUpdateCallback) {
      return function () {
        var promise = SessionModel.save(credentials).$promise
          .then(function () {
            return SessionModel.get().$promise;
          })
          .then(function (resp) {
            var user = resp.user;

            user.accepted_eula = state;

            return user.$update();
          })
          .then(dialog.close.bind(dialog));

        if (afterUpdateCallback) {
          promise = promise.then(afterUpdateCallback);
        }

        promise.then(doneCallback);
      };
    }

    $scope.eulaCtrl = {
      accept: createAction(true),
      reject: createAction(false, function () {
        return SessionModel.delete().$promise;
      }),
      eula: HELP_TEXT.eula
    };
  }

  angular.module('controllers')
    .controller('EulaCtrl', ['SessionModel', '$scope', 'dialog', 'HELP_TEXT', 'credentials', 'doneCallback', EulaCtrl]);
}());
