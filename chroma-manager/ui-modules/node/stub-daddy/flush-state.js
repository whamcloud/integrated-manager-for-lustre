//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

'use strict';

/**
 * Flushes the request store and mock status such that stub daddy is in a clean state.
 * @param {Object} requestStore
 * @param {Object} mockStatus
 * @param {Object} models
 * @param {Object} config
 * @returns {Function}
 */
exports.wiretree = function flushState (requestStore, mockStatus, models, config) {

  /**
   * Flushes both the request store and the mock status.
   * @param {Object} request
   * @returns {Number}
   */
  return function execute (request) {
    var registerResponse = new models.Response(config.status.BAD_REQUEST, config.standardHeaders);

    if (request.method === config.methods.DELETE) {
      // Flush all entries
      requestStore.flushEntries();
      mockStatus.flushRequests();

      registerResponse.status = config.status.SUCCESS;
    }

    return registerResponse;
  };
};
