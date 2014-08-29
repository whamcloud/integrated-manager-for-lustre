/*jshint node: true*/
'use strict';

/**
 * Returns the mock state
 * @param {Object} mockStatus
 * @param {Object} requestStore
 * @param {Object} config
 * @param {Object} models
 * @returns {Function}
 */
exports.wiretree = function mockStateModule(mockStatus, requestStore, config, models) {
  /**
   * Returns any error information contained in an object.
   * @returns {Object}
   */
  return function execute(request) {
    var incorrectMethodResponse = new models.Response(config.status.BAD_REQUEST, config.standardHeaders);
    if (request.method === config.methods.GET) {
      var errors = mockStatus.getMockApiState(requestStore);

      return {
        status: (errors.length > 0) ? config.status.BAD_REQUEST : config.status.SUCCESS,
        data: errors,
        headers: config.standardHeaders
      };
    }

    return incorrectMethodResponse;
  };
};
