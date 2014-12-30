'use strict';

var request = require('./request');
var _ = require('lodash');
var format = require('util').format;

module.exports = function getClient (config, validator) {
  var uri = format.bind(null, '%s://localhost:%s/%s', config.requestProtocol, config.port);

  return {
    /**
     * Add a new mock
     * @param {Object} mock
     * @returns {Object} A promise.
     */
    mock: function addMock (mock) {
      var errors = validator(mock).errors;

      if (errors.length > 0) {
        var message = format('The following mock is invalid: \n\n %s \n\n Reasons: \n\n %s',
          JSON.stringify(mock, null, 2),
          JSON.stringify(errors, null, 2)
        );
        throw new Error(message);
      }

      return makeRequest({
        path: 'api/mock',
        method: 'POST',
        json: mock
      });
    },
    /**
     * Retrieve the mock state.
     * @returns {Object} A promise.
     */
    mockState: function mockState () {
      return makeRequest({ path: 'api/mockstate' });
    },
    makeRequest: makeRequest
  };

  /**
   * Make a generic request
   * @param {Object} options
   * @returns {Object} A promise
   */
  function makeRequest (options) {
    options = _.merge({
      uri: uri(options.path),
      strictSSL: false,
      json: true
    }, options);
    delete options.path;

    return request(options);
  }
};
