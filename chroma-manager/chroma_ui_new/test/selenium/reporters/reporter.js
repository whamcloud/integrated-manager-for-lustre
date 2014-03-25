'use strict';

var format = require('util').format;
var path = require('path');
var mkdirp = require('mkdirp');

/**
 * Base reporter to inherit from
 * @param {Object} options Configuration.
 * @constructor
 */
function Reporter (options) {
  this.options = options || {};

  if (!this.options.prepend) this.options.prepend = '';
}

/**
 * Given a spec and file extension, returns a fleshed out file name.
 * @param {Object} spec The current spec.
 * @param {String} extension The extension of the file.
 * @returns {String} Returns the built file.
 */
Reporter.prototype.buildFileName = function buildFileName(spec, extension) {
  var description = joinDescriptions(spec.suite, [spec.description]);

  if (this.options.showDate)
    description = format('%s-%s', description, new Date().toISOString());

  var fileName = format('%s.%s', description, extension);

  if (this.options.prepend)
    fileName = format('%s-%s', this.options.prepend, fileName);

  return fileName;
};

/**
 * Builds the path of the file, taking extraPath into account
 * @param {Function} cb
 */
Reporter.prototype.buildPath = function buildPath(cb) {
  var newPath = path.join(process.cwd(), this.options.extraPath);

  mkdirp(newPath, function (err) {
    cb(err, newPath);
  });
};

/**
 * Given a suite and an array of spec descriptions,
 * recursively moves up the suite tree to build the full path.
 * @param {Object} suite Pointer to the current suite
 * @param {Array} soFar The list of descriptions
 * @returns {String} The full path description of the spec.
 */
function joinDescriptions(suite, soFar) {
  soFar.unshift(suite.description);

  if (suite.parentSuite)
    return joinDescriptions(suite.parentSuite, soFar);
  else
    return soFar.join(' ').replace(/\s/g, '-');
}

module.exports = Reporter;