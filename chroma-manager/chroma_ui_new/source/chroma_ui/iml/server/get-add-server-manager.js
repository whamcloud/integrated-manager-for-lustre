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


(function () {
  'use strict';

  angular.module('server')
    .constant('ADD_SERVER_STEPS', Object.freeze({
      ADD: 'addServersStep',
      STATUS: 'serverStatusStep',
      SELECT_PROFILE: 'selectServerProfileStep'
    }))
    .factory('addServerSteps', ['ADD_SERVER_STEPS', 'addServersStep', 'serverStatusStep', 'selectServerProfileStep',
      function addServerStepsFactory (ADD_SERVER_STEPS, addServersStep, serverStatusStep, selectServerProfileStep) {
        var steps = {};
        steps[ADD_SERVER_STEPS.ADD] = addServersStep;
        steps[ADD_SERVER_STEPS.STATUS] = serverStatusStep;
        steps[ADD_SERVER_STEPS.SELECT_PROFILE] = selectServerProfileStep;

        return steps;
      }
    ])
    .factory('getAddServerManager', ['addServerSteps', 'stepsManager', 'waitUntilLoadedStep', 'ADD_SERVER_STEPS',
      function getAddServerManagerFactory (addServerSteps, stepsManager, waitUntilLoadedStep, ADD_SERVER_STEPS) {
        return function getAddServerManager () {
          var manager = stepsManager();

          _.pairs(addServerSteps)
            .forEach(function addStep (pair) {
              manager.addStep(pair[0], pair[1]);
            });

          manager.addWaitingStep(waitUntilLoadedStep);
          manager.SERVER_STEPS = ADD_SERVER_STEPS;

          return manager;
        };
      }
  ]);
}());
