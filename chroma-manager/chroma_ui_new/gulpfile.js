/*jslint node: true */

'use strict';

var gulp = require('gulp'),
  gulpPrimus = require('./gulp-plugins/gulp-primus'),
  jshint = require('gulp-jshint'),
  stylish = require('jshint-stylish'),
  files = require('./gulp-src-globs.json'),
  uglify = require('gulp-uglify'),
  concat = require('gulp-concat'),
  rimraf = require('gulp-rimraf'),
  rev = require('gulp-rev'),
  minifyHtml = require('gulp-minify-html'),
  ngHtml2Js = require('gulp-ng-html2js');

[
  './gulp-tasks/less-tasks',
  './gulp-tasks/static-tasks',
  './gulp-tasks/write-js-tasks',
  './gulp-tasks/templates-tasks'
].map(function (file) {
  require(file)(gulp);
});

gulp.task('compress', ['primus', 'compile-templates'], function compress () {
  var sourceFiles = files.js.source
    .map(function (file) {
      return 'source/' + file;
    })
    .concat('tmp/partials.js');

  return gulp.src(sourceFiles)
    .pipe(concat('built.js'))
    .pipe(uglify({
      compress: {
        drop_debugger: true,
        drop_console: true
      }
    }))
    .pipe(rev())
    .pipe(gulp.dest('static/chroma_ui'));
});

gulp.task('compile-templates', ['clean-tmp'], function compileTemplates () {
  return gulp.src([
      'source/chroma_ui/**/*.html',
      '!source/chroma_ui/bower_components/**/*.html'
    ])
    .pipe(minifyHtml({
      quotes: true,
      empty: true
    }))
    .pipe(ngHtml2Js({
      moduleName: 'iml',
      prefix: '/static/chroma_ui/',
      stripPrefix: 'source/chroma_ui'
    }))
    .pipe(concat('partials.js'))
    .pipe(gulp.dest('tmp'));
});

gulp.task('clean-tmp', function() {
  return gulp.src(['tmp/**'], {read: false})
    .pipe(rimraf());
});

// Write primus client to destination
gulp.task('primus', function () {
  return gulpPrimus('../../realtime/generate-lib')
  .pipe(gulp.dest('source/chroma_ui/vendor/primus-client'));
});

// Run jshint
gulp.task('jshint', function() {
  var jsHintFiles = files.js.source.concat(
    'test/spec/**/*.js',
    'test/mock/**/*.js',
    'test/*.js',
    '!source/chroma_ui/bower_components/**/*.js',
    '!source/chroma_ui/vendor/**/*.js'
  );

  return gulp.src(jsHintFiles)
    .pipe(jshint('.jshintrc'))
    .pipe(jshint.reporter(stylish));
});

// The default task (called when you run `gulp`)
gulp.task('default', function() {
  gulp.run('copy-templates', 'less:dev');

  gulp.watch(files.js.source, function() {
    gulp.run('write-js:dev');
  });

  gulp.watch([
    'source/chroma_ui/**/*.less',
    '!source/chroma_ui/bower_components/**/*',
    '!source/chroma_ui/vendor/**/*'
  ], function() {
    gulp.run('less:dev');
  });

  gulp.watch('templates_source/**/*.html', function () {
    gulp.run('copy-templates');
  });
});

gulp.task('build', function build() {
  gulp.run('copy-templates', 'less:build', 'static:build');
});