/* jshint node:true */
'use strict';

var path = require('path');
var through = require('through');
var Buffer = require('buffer').Buffer;
var gutil = require('gulp-util');
var _ = require('lodash');
var PluginError = gutil.PluginError;
var plugName = 'gulp-srcmap-rev';

/**
 * Fixes the rev task.
 * Takes options that override behavior.
 * @param {Object} [opts]
 * @returns {Object}
 */
module.exports = function fixupRev (opts) {
  opts = _.defaults(opts, {
    transformSources: _.identity
  });

  var revFixFiles = {};

  return through(write);

  /**
   * Writes the map file to stream correctly.
   * Writes the built file as well.
   * @param {Object} data
   */
  function write (data) {
    /* jshint validthis: true */
    if (data.isNull()) return; // ignore
    if (data.isStream()) return this.emit('error', new PluginError(plugName, 'Streaming not supported'));

    add(path.basename(data.path), data);

    if (Object.keys(revFixFiles).length === 2) {
      // Set the rev hashes to match the built files rev hash.
      fixName();
      fixContents();

      // Add each file to the stream.
      this.queue(revFixFiles.built.vinyl);
      this.queue(revFixFiles.srcmap.vinyl);
    }
  }

  /**
   * Fix the name of the file in and outside of the vinyl file.
   */
  function fixName () {
    // Fix the name of the src map file
    revFixFiles.srcmap.name = revFixFiles.built.name + '.map';

    // Fix the name of the src map vinyl file
    revFixFiles.srcmap.vinyl.path = revFixFiles.srcmap.name;
  }

  /**
   * Fix the name within the contents of the vinyl file.
   */
  function fixContents () {
    // Fix the value of the src map json 'file' property
    // First, extract the json obj
    var srcMapJsonObj = JSON.parse(revFixFiles.srcmap.vinyl.contents);
    srcMapJsonObj.file = revFixFiles.srcmap.name;
    srcMapJsonObj.sources = srcMapJsonObj.sources.map(opts.transformSources);

    var stringy = JSON.stringify(srcMapJsonObj);

    // Reset the contents
    revFixFiles.srcmap.vinyl.contents = new Buffer(stringy);
  }

  /**
   * Add files to the buffered collection.
   * @param {String} baseName
   * @param {Object} vinylFile
   */
  function add (baseName, vinylFile) {
    var nameObj = {
      name: baseName,
      vinyl: vinylFile
    };

    if (baseName.indexOf('.map') !== -1)
      revFixFiles.srcmap = nameObj;
    else
      revFixFiles.built = nameObj;
  }
};
