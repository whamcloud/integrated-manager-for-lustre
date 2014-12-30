'use strict';

var request = require('request-then');

module.exports = function makeRequest (options) {
  return request(options)
    .then(function handleServerErrors (response) {
      if (response.statusCode < 400) {
        return response;
      }  else {
        var message = 'unexpected status code: ' + response.statusCode + '\n';

        try {
          message += JSON.stringify(response.body, null, 2);
        } catch (e) {
          message += response.body;
        }

        var error = new Error(message);
        error.statusCode = response.statusCode;
        error.headers = response.headers;
        error.body = response.body;

        throw error;
      }
    });
};
