/*jslint node: true */

'use strict';

var rimraf = require('gulp-rimraf');

module.exports = function (gulp) {
  gulp.task('static:dev', ['clean-static'], moveToStatic.bind({
    src: [
      'source/chroma_ui/**/*.{html,js,png,woff,ttf,svg,ico}',
      '!source/chroma_ui/**/{*.min.js,Gruntfile.js}'
    ]
  }));

  gulp.task('static:build', ['clean-static'], moveToStatic.bind({
    src: [
      'source/chroma_ui/**/*.{png,woff,ttf,svg,ico}'
    ]
  }));

  function moveToStatic () {
    /* jshint validthis: true */
    return gulp.src(this.src)
      .pipe(gulp.dest('static/chroma_ui'));
  }

  gulp.task('clean-static', function() {
    return gulp.src(['static/**'], {read: false})
      .pipe(rimraf());
  });
};