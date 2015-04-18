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
 *
 * @param {Function} requestMatcher
 * @param {Object} models
 * @param {Logger} logger
 * @param {Object} _ lodash
 * @param {Object} mockStatus
 * @returns {Object}
 */
exports.wiretree = function requestStoreModule(requestMatcher, models, logger, _, mockStatus) {
  var entries = [];

  return {
    /**
     * Adds a new entry to the store.
     * @param {models.Request} request
     * @param {models.Response} response
     * @param {Number} expires
     * @param {Array} dependencies
     */
    addEntry: function addEntry(request, response, expires, dependencies) {
      logger.logByLevel({
        DEBUG: [{url: request.url}, 'adding entry to request store.'],
        TRACE: [{
          request: request,
          response: response,
          expires: expires,
          dependencies: dependencies
        }, 'adding entry to request store: ']
      });

      entries.push(new models.RequestEntry(request, response, expires, dependencies));
    },
    /**
     * Searches for the specified request in the list of entries. Returns the entry when it is found.
     * @param {models.Request} request
     * @return {models.RequestEntry[]|null}
     */
    findEntriesByRequest: function findEntriesByRequest(request) {
      var filteredEntries = entries.filter(function filterEntries(element) {
        return requestMatcher(request, element.request);
      });

      if (filteredEntries.length > 0) {
        var getData = _.flip(_.get, 'request.data');
        var equalsData =  _.flip(_.isEqual, request.data);
        var dataEqual = _.flow(getData, equalsData);

        // Multiple matches may have been found, some potentially with exact matches to the request and some that
        // don't. Filter these such that if there are any exact matches they will be extracted.
        var selectedEntries = _.filter(filteredEntries, dataEqual);
        if (!selectedEntries.length)
          selectedEntries = filteredEntries;

        selectedEntries = selectedEntries.filter(function filterOutEntriesWithUnsatisfiedDependencies (entry) {
          return mockStatus.haveRequestsBeenSatisfied(this, entry.dependencies);
        }, this);

        logger.logByLevel({
          DEBUG: ['found entry by request', request.url],
          TRACE: [{
            request: request,
            entries: selectedEntries
          }, 'found entry by request']
        });

        return selectedEntries;
      } else {
        logger.warn({request: request}, 'entry for request not found');

        return null;
      }
    },

    /**
     * Allows clients to specify a filter function and return entries that match the filter. If no
     * filter is passed all entries will be returned.
     * @param {Function} [filter]
     * @returns {Array}
     */
    getEntries: function getEntries(filter) {
      filter = filter || _.identity;
      return filter(entries);
    },

    /**
     * Flush the entries.
     */
    flushEntries: function flushEntries() {
      logger.info('flushing request store entries');

      // reset the entries array.
      entries.length = 0;
    }
  };
};
