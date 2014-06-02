/* jshint node:true */
'use strict';

var gulp = require('gulp');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');
var concat = require('gulp-concat');
var rev = require('gulp-rev');
var transformFooter = require('./lib/transform-footer');

/**
 * Uglifies many javascript and html template files into one javascript file.
 * Also, creates a source map file for the uglified file.
 * @param {Function} enqueueStreams
 * @param {Function} compileTemplates
 * @param {Function} generatePrimusClientLib
 * @param {Array} sourceFiles
 * @param {String} destination
 * @return {Stream}
 */
module.exports = function createSourceMap (
  enqueueStreams,
  compileTemplates,
  generatePrimusClientLib,
  sourceFiles,
  destination) {

  // Orders the streams into one stream.
  // Also, creates the compiled javascript file and sourcemap file.
  // Writes the two files mentioned above to "destination".
  return enqueueStreams(generatePrimusClientLib, gulp.src(sourceFiles), compileTemplates)
    .pipe(sourcemaps.init())
    .pipe(concat('built.js'))
    .pipe(uglify(uglyOptions))
    .pipe(rev())
    .pipe(transformFooter())
    .pipe(sourcemaps.write('./', { addComment: false }))
    .pipe(gulp.dest(destination));

};

// Uglify and Source Map options.
var uglyOptions = Object.freeze({
  compress: {
    drop_debugger: true,
    drop_console: true
  },
  outSourceMap: true
});
