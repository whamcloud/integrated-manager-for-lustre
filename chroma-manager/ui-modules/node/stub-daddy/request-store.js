/*jshint node: true*/
'use strict';

/**
 *
 * @param {Function} requestMatcher
 * @param {Object} models
 * @param {Logger} logger
 * @returns {Object}
 */
exports.wiretree = function requestStoreModule(requestMatcher, models, logger) {
  var entries = [];

  return {
    /**
     * Adds a new entry to the store.
     * @param {models.Request} request
     * @param {models.Response} response
     * @param {Number} expires
     */
    addEntry: function addEntry(request, response, expires) {
      logger.info('adding entry to request store');
      logger.debug({
        request: request,
        response: response,
        expires: expires
      }, 'adding entry to request store');

      entries.push(new models.RequestEntry(request, response, expires));
    },
    /**
     * Searches for the specified request in the list of entries. Returns the entry when it is found.
     * @param {models.Request} request
     * @return {models.RequestEntry|null}
     */
    findEntryByRequest: function findEntryByRequest(request) {
      var entry = entries.filter(function filterEntries(element) {
        return requestMatcher(request, element.request);
      }).shift();

      if (entry) {
        logger.info('found entry by request');
        logger.debug({
          request: request,
          entry: entry
        }, 'found entry by request');
      } else {
        logger.info('entry for request not found');
        logger.debug({
          request: request
        }, 'entry for request not found');
      }

      return entry;
    },

    /**
     * Allows clients to specify a filter function and return entries that match the filter. If no
     * filter is passed all entries will be returned.
     * @param {Function} [filter]
     * @returns {Array}
     */
    getEntries: function getEntries(filter) {
      return (typeof filter === 'function') ? filter(entries) : entries;
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
