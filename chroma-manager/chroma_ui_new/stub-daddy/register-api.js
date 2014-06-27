/*jshint node: true*/
'use strict';

/**
 * Registers an API
 * @param {Object} requestStore
 * @param {Object} models
 * @param {Object} config
 * @param {Function} registerApiValidator
 * @param {Logger} logger
 * @returns {Function}
 */
exports.wiretree = function registerApiModule(requestStore, models, config, registerApiValidator, logger) {
  /**
   * Validates that the body contains the request, response, and expires properties
   * @param {Object} body
   * @returns {Boolean}
   */
  function validate(body) {
    return registerApiValidator(body).errors.length === 0;
  }

  /**
   * Creates a new request and response object and sends it to the request store.
   * @param {Object} request
   * @param {Object} body
   * @returns {Number}
   */
  return function execute(request, body) {
    var registerResponse = new models.Response(config.status.BAD_REQUEST, config.standardHeaders);

    if (request.method === config.methods.POST && validate(body)) {
      var newRequest = new models.Request(
        body.request.method,
        body.request.url,
        body.request.data,
        body.request.headers
      );

      var newResponse = new models.Response(
        body.response.status,
        body.response.headers,
        body.response.data
      );

      logger.info('registering request');
      requestStore.addEntry(newRequest, newResponse, body.expires);

      registerResponse.status = config.status.CREATED;
    }

    return registerResponse;
  };
};
