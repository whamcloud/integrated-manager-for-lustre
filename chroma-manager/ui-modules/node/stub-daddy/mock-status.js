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
 * Returns the mock status
 * @param {Function} requestMatcher
 * @param {Logger} logger
 * @param {Object} _
 * @returns {Object}
 */
exports.wiretree = function mockStatusModule (requestMatcher, logger, _) {
  return {
    requests: [],

    /**
     * Records an incoming request.
     * @param {models.Request} request
     */
    recordRequest: function recordRequest (request) {
      // Locate the request in the requests dictionary.
      var locatedRequest = this.requests.filter(function filterRequest (curRequest) {
        return requestMatcher(request, curRequest);
      }).shift();

      // Only add the request if it isn't in the requests list.
      if (!locatedRequest) {
        logger.trace({
          request: request
        }, 'recording request to list of requests made');
        this.requests.push(request);
      }
    },

    /**
     * Returns the mock api state based on registered calls. This method simply checks for any unregistered
     * calls and for any registered calls that have not been called.
     * @param {Object} requestStore
     * @returns {Array}
     */
    getMockApiState: function getMockApiState (requestStore) {
      var unregisteredCalls = this.getCallsMadeToUnregisteredRequests(requestStore);
      var unsatisfiedEntries = this.getUnsatisfiedEntries(requestStore);

      var state = unregisteredCalls
        .map(generateErrorMessagesForArray('Call made to non-existent mock'))
        .concat(unsatisfiedEntries
          .map(generateErrorMessagesForArray('Call to expected mock not satisfied.'))
      );

      logger.trace({
        state: state
      }, 'mock API state');

      if (state.length === 0)
        logger.trace('mock API state is passing');
      else
        logger.trace('mock API state contains ' + state.length + ' errors');

      return state;

      /**
       * Higher order function used to generate the error object based on a message being passed in.
       * @param {String} message
       * @returns {Function}
       */
      function generateErrorMessagesForArray (message) {
        return function create (item) {
          return {
            state: 'ERROR',
            message: message,
            data: item
          };
        };
      }
    },

    /**
     * Get calls made to any unregistered requests.
     * @param {Object} requestStore
     * return {Array}
     */
    getCallsMadeToUnregisteredRequests: function getCallsMadeToUnregisteredRequests (requestStore) {
      return this.requests.filter(function (curRequest) {
        return requestStore.findEntriesByRequest(curRequest) == null;
      });
    },

    /**
     * Returns entries that are not satisfied.
     * @param {Object} requestStore
     * @returns {Array}
     */
    getUnsatisfiedEntries: function getUnsatisfiedEntries (requestStore) {
      function getEntries (entries) {
        return entries.filter(function (entry) {
          return !entry.isExpectedCallCount();
        });
      }

      return requestStore.getEntries(getEntries);
    },

    /**
     * Accepts a list of requests and verifies that each request has been satisfied.
     * @param {Object} requestStore
     * @param {Array} requests
     * @returns {boolean}
     */
    haveRequestsBeenSatisfied: function haveRequestsBeenSatisfied (requestStore, requests) {
      if (requests.length === 0)
        return true;

      /**
       * Create a matching function that matches the url, method, and data exactly. We aren't concerned about
       * the headers being exact. As long as the request used all header properties specified in the mock it can
       * have additional headers and it won't be a problem.
       * @param {Object} req1
       * @param {Object} req2
       * @returns {boolean|*}
       */
      function matchRequest (req1, req2) {
        return req1.url === req2.url &&
          req1.method === req2.method &&
          _.isEqual(req1.data, req2.data) &&
          Object.keys(req1.headers).every(function (header) {
            return req1.headers[header] === req2.headers[header];
          });
      }

      /**
       * Function used to retrieve only those entries that match the request using matchRequest.
       * @param {Array} entries
       * @returns {*}
       */
      function getEntries (entries) {
        return entries.filter(function (entry) {
          return requests.some(function filterByRequest (request) {
            return matchRequest(entry.request, request);
          });
        });
      }

      var filteredEntries = requestStore.getEntries(getEntries);
      if (filteredEntries.length !== requests.length)
        return false;

      return filteredEntries.every(function verifyAllEntriesSatisfied (entry) {
        return entry.isExpectedCallCount();
      });
    },

    /**
     * Flushes the requests array.
     */
    flushRequests: function flushRequests () {
      this.requests.length = 0;
    }
  };
};
