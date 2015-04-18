/*jshint node: true*/
'use strict';

/**
 * Returns a function that will validate a mock API request against the required mock API request schema.
 * @returns {Function}
 */
exports.wiretree = function registerApiValidatorModule(Validator) {

  // request schema
  var requestSchema = {
    id: '/RegisterRequest',
    type: 'object',
    required: true,
    properties: {
      method: {type: 'string', required: true},
      url: {type: 'string', required: true},
      data: {type: 'object', required: true},
      headers: {type: 'object', required: true}
    }
  };

  // response schema
  var responseSchema = {
    id: '/RegisterResponse',
    type: 'object',
    required: true,
    properties: {
      status: {type: 'integer', required: true},
      data: {type: 'object', required: true},
      headers: {type: 'object', required: true}
    }
  };

  // Optional Dependencies
  var dependenciesSchema = {
    id: '/RegisterDependencies',
    type: 'array',
    required: true,
    items: {
      type: 'object',
      properties: {
        method: {type: 'string', required: true},
        url: {type: 'string', required: true},
        data: {type: 'object', required: true},
        headers: {type: 'object', required: true}
      }
    }
  };

  // body schema
  var bodySchema = {
    id: '/RegisterApi',
    type: 'object',
    required: true,
    properties: {
      request: { $ref: '/RegisterRequest'},
      response: { $ref: '/RegisterResponse'},
      dependencies: { $ref: '/RegisterDependencies'},
      expires: {type: 'integer', 'minimum': 0, required: true}
    }
  };

  /**
   * Validates the body against the RegisterApi schema
   * @param {Object} body The body to validate
   * @return {Object} object containing array of errors
   */
  return function validate(body) {
    var v = new Validator();

    // json schema doesn't handle a null body but it will handle undefined. Cast this to
    // undefined in either case.
    if (body == null)
      body = undefined;

    v.addSchema(requestSchema, '/RegisterRequest');
    v.addSchema(responseSchema, '/RegisterResponse');
    v.addSchema(dependenciesSchema, '/RegisterDependencies');
    return v.validate(body, bodySchema);
  };

};
