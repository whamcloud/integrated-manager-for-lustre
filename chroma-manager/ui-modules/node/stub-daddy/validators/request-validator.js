/*jshint node: true*/
'use strict';

/**
 * Returns a function that will validate a request.
 * @param {Function} Validator
 * @returns {Function}
 */
exports.wiretree = function requestValidatorModule(Validator) {

  var schema = {
    id: '/schema',
    type: 'object',
    required: true,
    properties: {
      url: { type: 'string', minimum: 0, required: true},
      method: { type: 'string', minimum: 0, required: true},
      body: { type: 'object' },
      headers: { type: 'object', required: true }
    }
  };

  /**
   * Validates the body of a request.
   * @param {Object} body The body to validate
   * @returns {Object} object containing array of errors
   */
  return function validate (body) {
    var v = new Validator();

    body = (body) ? body : undefined;

    return v.validate(body, schema);
  };
};
