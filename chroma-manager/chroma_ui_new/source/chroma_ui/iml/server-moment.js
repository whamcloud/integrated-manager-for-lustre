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

  angular.module('serverMoment', [])
    .factory('getServerMoment', ['moment', 'SERVER_TIME_DIFF', getServerMomentFactory]);

  /**
   * Returns a getServerMoment function.
   * @param {Object} moment
   * @param {String} SERVER_TIME_DIFF
   * @returns {Function}
   */
  function getServerMomentFactory(moment, SERVER_TIME_DIFF) {
    /**
     * Creates a new moment with forwarded arguments.
     * The moment is then updated with SERVER_TIME_DIFF
     * and returned.
     * @returns {Object}
     */
    return function getServerMoment() {
      return moment
        .apply(moment, arguments)
        .add(SERVER_TIME_DIFF);
    };
  }
}());
