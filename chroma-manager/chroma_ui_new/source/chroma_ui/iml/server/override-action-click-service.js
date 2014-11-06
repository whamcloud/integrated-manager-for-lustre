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

angular.module('server')
  .factory('overrideActionClick', ['ADD_SERVER_STEPS', 'openAddServerModal', '$q',
    function overrideActionClickService (ADD_SERVER_STEPS, openAddServerModal, $q) {
      'use strict';
      return function overrideActionClickFactory (serverSpark) {
        return function overrideActionClick (record, action) {
          var notRemoving = (action.state && action.state !== 'removed') && action.verb !== 'Force Remove';
          var openForDeploy = record.state === 'undeployed';
          var openForConfigure = (record.server_profile && record.server_profile.initial_state === 'unconfigured');

          if ((openForDeploy || openForConfigure) && notRemoving) {
            var step;
            if (record.install_method !== 'existing_keys_choice')
              step = ADD_SERVER_STEPS.ADD;
            else if (openForDeploy)
              step = ADD_SERVER_STEPS.STATUS;
            else
              step = ADD_SERVER_STEPS.SELECT_PROFILE;

            return openAddServerModal(serverSpark, record, step).result;
          } else {
            return $q.when('fallback');
          }
        };
      };
    }
  ]);
