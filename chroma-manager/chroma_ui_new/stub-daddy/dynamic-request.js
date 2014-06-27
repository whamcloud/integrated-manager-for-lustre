/*jshint node: true*/
'use strict';

/**
 * Wiretree export.
 * @param {Object} mockStatus
 * @param {Object} requestStore
 * @param {Object} models
 * @param {Logger} logger
 * @returns {Function}
 */
exports.wiretree = function dynamicRequestModule(mockStatus, requestStore, models, logger) {

  /**
   * Processes the dynamic request.
   * @param {http.IncomingMessage} request
   * @param {http.IncomingMessage} body
   * @returns {RequestEntry}
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

    logger.debug({
      searchRequest: searchRequest
    }, 'new search request instance created');

    // record the request in the mock state module.
    mockStatus.recordRequest(searchRequest);

    /**
     * @type {RequestEntry} entry
     */
    var entry = requestStore.findEntryByRequest(searchRequest);

    logger.debug({
      entry: entry
    }, 'entry from request store matching the request');

    var response = null;
    if (entry) {
      if (entry.canMakeRequest()) {
        response = entry.response;
      }

      // decrement the expires value regardless of whether or not you can make the request.
      entry.updateCallCount();
    }

    return response;
  };
};
