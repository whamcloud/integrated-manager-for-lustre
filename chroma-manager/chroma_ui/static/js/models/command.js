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


angular.module('models').factory('commandModel', ['baseModel', 'STATES', function (baseModel, STATES) {
  'use strict';

  return baseModel({
    url: '/api/command/:commandId',
    params: {commandId: '@id'},
    methods: {
      /**
       * @description Returns the state of the command.
       * @returns {string}
       */
      getState: function () {
        if (!this.complete) {
          return STATES.INCOMPLETE;
        } else if (this.errored) {
          return STATES.ERROR;
        } else if (this.cancelled) {
          return STATES.CANCELED;
        } else {
          return STATES.COMPLETE;
        }
      },
      getName: function () {
        return 'command';
      },
      /**
       * Command should not be dismissed if it's incomplete.
       * @returns {boolean}
       */
      notDismissable: function () {
        return !this.complete;
      },
      noDismissMessage: function () {
        return 'no_dismiss_message_command';
      }
    }
  });
}]);
