/*jshint node: true*/
'use strict';

var dotty = require('dotty');
var registerApiValidator;

describe('test register api body against validator', function() {
  var body;
  var config = {
    methods: {
      POST: 'POST'
    }
  };
  var Validator = require('jsonschema').Validator;

  beforeEach(function() {
    body = {
      request: {
        method: config.methods.POST,
        url: '/user/profile',
        data: {
          user: 'johndoe',
          key: 'abc123'
        },
        headers: {
          authorization: 'BEARER token55'
        }
      },
      response: {
        status: 200,
        data: {
          firstName: 'John',
          lastName: 'Doe',
          dob: '1981-09-07',
          city: 'Orlando',
          state: 'FL'
        },
        headers: {
          authorization: 'BEARER token55'
        }
      },
      expires: 0
    };


    registerApiValidator = require('../../validators/register-api-validator').wiretree(Validator);
  });

  it('should validate the body with a successful response', function() {
    var result = registerApiValidator(body);
    expect(result.errors.length).toEqual(0);
  });

  it('should validate a string with a failed response', function() {
    var result = registerApiValidator('some string');
    expect(result.errors.length).toEqual(4);
  });

  it('should validate an undefined body with a failed response', function() {
    var result = registerApiValidator(undefined);
    expect(result.errors.length).toEqual(1);
  });

  it('should validate a null body with a failed response', function() {
    var result = registerApiValidator(null);
    expect(result.errors.length).toEqual(1);
  });


  var bodyComponents = [
    'request.method',
    'request.url',
    'request.data',
    'request.headers',
    'response.status',
    'response.data',
    'response.headers',
    'expires',
    'request',
    'response'
  ];
  bodyComponents.forEach(function (element) {
    it('should validate the body with a failed response due to a missing required field', function () {
      dotty.remove(body, element);
      var result = registerApiValidator(body);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

});
