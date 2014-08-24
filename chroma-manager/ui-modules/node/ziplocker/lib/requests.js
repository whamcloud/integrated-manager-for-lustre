'use strict';

/**
 * Exposes request handling for Promises and Streams.
 * @param {Object} config
 * @param {Function} requestThen
 * @param {Function} request
 * @returns {{requestThen: Function, requestPipe: Function}}
 */
exports.wiretree = function requestsModule (config, requestThen, request) {
  return {
    /**
     * Wraps requestThen.
     * @param {String} path
     * @returns {Promise}
     */
    requestThen: function reqThen (path) {
      return requestThen(getOptions(path));
    },
    /**
     * Wraps request.
     * @param {String} path
     * @returns {Stream}
     */
    requestPipe: function requestPipe (path) {
      return request(getOptions(path));
    }
  };

  /**
   * Parses the response body as JSON.
   * Adds the proxy if set.
   * @param {String} path
   * @returns Object
   */
  function getOptions (path) {
    var options = {
      uri: path,
      json: true
    };

    if (typeof config.proxyUrl === 'string')
      options.proxy = config.proxyUrl;

    return options;
  }
};
