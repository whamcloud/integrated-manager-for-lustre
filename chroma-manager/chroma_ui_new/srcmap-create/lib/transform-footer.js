/* jshint node:true */
'use strict';

var mapStream = require('map-stream');
var path = require('path');
var util = require('util');

/**
 * Appends the src map url to the end of the Vinyl file.
 * @return {Object} A stream.
 */
module.exports = function transformFooter () {

  /**
   * Create a through stream (readable & writable) stream from the transform()
   * function.
   */
  return mapStream(transform);

};

/**
 * Async func to transform the Vinyl file.
 * @param {Object} vinylFile Vinyl file of which the path and contents properties
 * are used to create the src map url.
 * @param {Function} cb Execs the callback with the transformed data.
 */
function transform (vinylFile, cb) {

  /**
   * Create a string containing the minified file contents,
   * and the location on disk of the source map file.
   * This happens by removing the original value by using
   * Array#pop() and appending '.map' to it.
   */
  var str = util.format(
    '%s\n//# sourceMappingURL=%s.map',
    vinylFile.contents,
    path.resolve(vinylFile.path)
      .split(path.sep)
      .pop()

  );

  /**
   * Allocates a new Buffer (Octet Stream) containing the given str,
   * with default encoding of 'utf8'.
   */
  vinylFile.contents = new Buffer(str);

  /**
   * Call the callback
   * ref: https://github.com/dominictarr/map-stream#map-asyncfunction-options
   */
  cb(null, vinylFile);
}
