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
 * Wiretree export.
 * @param {Object} mockStatus
 * @param {Object} requestStore
 * @param {Object} models
 * @param {Logger} logger
 * @param {Object} _
 * @returns {Function}
 */
exports.wiretree = function dynamicRequestModule(mockStatus, requestStore, models, logger, _) {

  /**
   * Processes the dynamic request.
   * @param {http.IncomingMessage} request
   * @param {http.IncomingMessage} body
   * @returns {Response|null|undefined}
   */
  return function process(request, body) {
    /**
     * @type {Request} searchRequest
     */
    var searchRequest = new models.Request(
      request.method,
      request.url,
      body || {},
      request.headers);

    logger.trace({
      searchRequest: searchRequest
    }, 'new search request instance created');

    // record the request in the mock state module.
    mockStatus.recordRequest(searchRequest);

    /**
     * @type {RequestEntry} entry
     */
    var entries = requestStore.findEntriesByRequest(searchRequest);

    if (entries == null)
      return null;

    var canMakeRequest = _.flip(_.result, 'canMakeRequest');
    var entry = _.filter(entries, canMakeRequest)[0] || entries[0];

    logger.trace({
      entry: entry
    }, 'entry from request store matching the request');

    entry.updateCallCount();

    if (entry.hasRemainingCalls())
      return entry.response;
  };
};
