/*jslint node: true */

'use strict';

var rimraf = require('gulp-rimraf');

module.exports = function (gulp) {
  gulp.task('copy-templates', ['clean-templates'], function copyTemplates() {
    return gulp.src([
        'templates_source/chroma_ui/**/*.html',
        '!templates_source/chroma_ui/base.html'
      ])
      .pipe(gulp.dest('templates/chroma_ui'));
  });

  gulp.task('clean-templates', function() {
    return gulp.src(['templates/**'], {read: false})
      .pipe(rimraf());
  });
};