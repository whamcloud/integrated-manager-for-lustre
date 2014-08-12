/* jshint node:true */
'use strict';

var gulp = require('gulp');
var rev = require('gulp-rev');
var srcmapRev = require('./lib/gulp-srcmap-rev');
var transformFooter = require('./lib/gulp-transform-srcmaps-footer');
var minAndMap = require('./lib/gulp-min-and-map');

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
module.exports = function createSourceMap(enqueueStreams, compileTemplates,
  generatePrimusClientLib,
  sourceFiles, destination) {

  return enqueueStreams(generatePrimusClientLib, gulp.src(sourceFiles),
  compileTemplates)
    .pipe(minAndMap('built.js'))
    .pipe(rev())
    .pipe(srcmapRev)
    .pipe(transformFooter())
    .pipe(gulp.dest(destination));

};
