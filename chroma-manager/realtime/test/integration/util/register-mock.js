'use strict';

var request = require('request');

module.exports = function registerMock (json, done) {
  request({
    url: 'https://localhost:8000/api/mock',
    method: 'POST',
    json: json
  }, function (err) {
    if (err)
      throw err;

    done();
  });
};
