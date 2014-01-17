/*jslint node: true */

'use strict';

var less = require('gulp-less'),
  csso = require('gulp-csso'),
  rev = require('gulp-rev'),
  gulpWrite = require('../gulp-plugins/gulp-write');

module.exports = function (gulp) {
  gulp.task('less:dev', ['write-js:dev'], function writeLessDev() {
    return createLess()
      .pipe(gulp.dest('static/chroma_ui/styles'))
      .pipe(gulpWrite('templates/chroma_ui/base.html', 'writecss'))
      .pipe(gulp.dest('templates/chroma_ui'));
  });

  gulp.task('less:build', ['write-js:build'], function lessBuild() {
    return createLess()
      .pipe(csso())
      .pipe(rev())
      .pipe(gulp.dest('static/chroma_ui/styles'))
      .pipe(gulpWrite('templates/chroma_ui/base.html', 'writecss'))
      .pipe(gulp.dest('templates/chroma_ui'));
  });

  function createLess () {
    return gulp.src('source/chroma_ui/styles/imports.less')
      .pipe(less({
        relativeUrls: false,
        rootpath: '',
        paths: ['source/chroma_ui/']
      }));
  }
};