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


angular.module('server').factory('runServerAction', ['socket', function runServerActionFactory (socket) {
  'use strict';

  /**
   * Given an action and list of hosts
   * Does a post performing the action on those hosts.
   * @param {Object} action
   * @param {Array} hosts
   */
  return function runServerAction (action, hosts) {
    var spark = socket('request');

    spark.send('req', {
      path: '/command',
      options: {
        method: 'post',
        json: {
          message: action.message,
          jobs: action.convertToJob(hosts)
        }
      }
    }, ack);

    /**
     * Ack handler for the post.
     * @param {Object} response
     */
    function ack (response) {
      if ('error' in response)
        throw response.error;

      console.log(response);
    }
  };
}]);
