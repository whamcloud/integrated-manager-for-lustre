'use strict';

var request = require('https').request;
var PassThrough = require('stream').PassThrough;

module.exports = function makeRequest (options, buffer) {
  var s = new PassThrough();
  var req = request(options, function handleResponse (r) {
    r.on('error', handleError);
    if (r.statusCode >= 400) {
      var err = new Error();
      err.statusCode = r.statusCode;
      handleError(err, true);
    }

    s.responseHeaders = r.headers;
    r.pipe(s);
  });
  if (buffer) {
    req.setHeader('content-length', buffer.length);
    req.write(buffer);
  }
  req.on('error', handleError);
  req.end();
  return s;
  function handleError (err, keepOpen) {
    s.emit('error', err);
    if (!keepOpen)
      s.end();
  }
};
