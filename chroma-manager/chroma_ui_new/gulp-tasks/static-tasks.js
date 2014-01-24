/*jslint node: true */

'use strict';

var rimraf = require('gulp-rimraf');

module.exports = function (gulp) {
  gulp.task('static:dev', ['clean-static'], moveToStatic.bind({
    src: [
      'source/chroma_ui/**/*.{html,js,png,woff,ttf,svg,ico}',
      '!source/chroma_ui/**/{*.min.js,Gruntfile.js}',
      '!source/chroma_ui/bower_components/bootstrap/**',
      '!source/chroma_ui/bower_components/font-awesome/src/**',
      '!source/chroma_ui/bower_components/jasmine-stealth',
      '!source/chroma_ui/bower_components/jquery/jquery-migrate.js',
      '!source/chroma_ui/bower_components/lodash/dist/lodash.*.js',
      '!source/chroma_ui/bower_components/angular-route-segment/src/**',
      '!source/chroma_ui/bower_components/angular-route-segment/karma-*.js',
      '!source/chroma_ui/bower_components/{moment,momentjs}/lang/**',
      '!source/chroma_ui/bower_components/{moment,momentjs}/min/**',
      '!source/chroma_ui/bower_components/ngstorage/test/**',
      '!source/chroma_ui/bower_components/nvd3/GruntFile.js',
      '!source/chroma_ui/bower_components/twix/{test,vendor}/**',
      '!source/chroma_ui/bower_components/twix/bin/lang/**',
      '!source/chroma_ui/bower_components/underscore-contrib/{dist,test}/**',
      '!source/chroma_ui/bower_components/underscore-contrib/index.html',
      '!source/chroma_ui/bower_components/underscore-contrib/index.js'
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
    return gulp.src([
      'static/chroma_ui/**/*.{html,js,png,woff,ttf,svg,ico}'
    ], {read: false})
      .pipe(rimraf());
  });
};