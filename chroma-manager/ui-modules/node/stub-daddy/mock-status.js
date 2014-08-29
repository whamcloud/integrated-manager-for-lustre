/*jshint node: true*/
'use strict';

/**
 * Returns the mock status
 * @param {Function} requestMatcher
 * @param {Logger} logger
 * @returns {Object}
 */
exports.wiretree = function mockStatusModule(requestMatcher, logger) {
  return {
    requests: [],

    /**
     * Records an incoming request.
     * @param {models.Request} request
     */
    recordRequest: function recordRequest(request) {
      // Locate the request in the requests dictionary.
      var locatedRequest = this.requests.filter(function filterRequest(curRequest) {
        return requestMatcher(request, curRequest);
      }).shift();

      // Only add the request if it isn't in the requests list.
      if (!locatedRequest) {
        logger.debug({
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
    getMockApiState: function getMockApiState(requestStore) {
      var unregisteredCalls = this.getCallsMadeToUnregisteredRequests(requestStore);
      var unsatisfiedEntries = this.getUnsatisfiedEntries(requestStore);

      var state = unregisteredCalls
        .map(generateErrorMessagesForArray('Call made to non-existent mock'))
        .concat(unsatisfiedEntries
          .map(generateErrorMessagesForArray('Call to expected mock not satisfied.'))
      );

      logger.debug({
        state: state
      }, 'mock API state');

      if (state.length === 0)
        logger.info('mock API state is passing');
      else
        logger.info('mock API state contains ' + state.length + ' errors');

      return state;

      /**
       * Higher order function used to generate the error object based on a message being passed in.
       * @param {String} message
       * @returns {Function}
       */
      function generateErrorMessagesForArray(message) {
        return function create(item) {
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
    getCallsMadeToUnregisteredRequests: function getCallsMadeToUnregisteredRequests(requestStore) {
      return this.requests.filter(function (curRequest) {
        return requestStore.findEntryByRequest(curRequest) == null;
      });
    },

    /**
     * Returns entries that are not satisfied.
     * @param {Object} requestStore
     * @returns {Array}
     */
    getUnsatisfiedEntries: function getUnsatisfiedEntries(requestStore) {
      function getEntries(entries) {
        return entries.filter(function (entry) {
          return !entry.isExpectedCallCount();
        });
      }

      return requestStore.getEntries(getEntries);
    },

    /**
     * Flushes the requests array.
     */
    flushRequests: function flushRequests() {
      this.requests.length = 0;
    }
  };
};
