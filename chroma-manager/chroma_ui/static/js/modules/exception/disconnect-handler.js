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

  function disconnectHandlerFactory(disconnectDialog, interval, replay) {
    var clearIntervalFunc, goPromise;

    return {
      add: function add(config) {
        var promise = replay.add(config);

        // We are already processing.
        if (clearIntervalFunc) return promise;

        clearIntervalFunc = interval(checkAndClear, 5000, false);

        if (!disconnectDialog.isOpen()) disconnectDialog.open();

        return promise;
      }
    };

    function checkAndClear() {
      // We are already processing.
      if (goPromise) return;

      goPromise = replay.go();

      goPromise.finally(function cleanup() {
        //Flag we are not processing the queue anymore.
        goPromise = null;

        if (!replay.hasPending) {
          clearIntervalFunc();
          clearIntervalFunc = null;

          disconnectDialog.close();
        }
      });
    }
  }

  angular.module('exception').factory('disconnectHandler',
    ['disconnectDialog', 'interval', 'replay', disconnectHandlerFactory]);
}());
