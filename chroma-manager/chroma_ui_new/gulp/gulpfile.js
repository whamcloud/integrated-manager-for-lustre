'use strict';

var del = require('del');
var gulp = require('gulp');
var cache = require('gulp-cached');
var csso = require('gulp-csso');
var gulpIf = require('gulp-if');
var injector = require('gulp-inject');
var jscs = require('gulp-jscs');
var jshint = require('gulp-jshint');
var less = require('gulp-less');
var minifyHtml = require('gulp-minify-html');
var ngHtml2Js = require('gulp-ng-html2js');
var plumber = require('gulp-plumber');
var rev = require('gulp-rev');
var stylish = require('jshint-stylish');
var minimist = require('minimist');
var streamqueue = require('streamqueue');

var sourcemaps = require('gulp-sourcemaps');
var concat = require('gulp-concat');
var uglify = require('gulp-uglify');
var gulpPrimus = require('./lib/gulp-primus');
var iifeWrap = require('./lib/gulp-iife-wrap');
var annotate = require('./lib/gulp-annotate');

var files = require('../gulp-src-globs.json');
var qualityFiles = files.js.source.concat(
  'test/spec/**/*.js',
  'test/mock/**/*.js',
  'test/*.js',
  '!source/chroma_ui/bower_components/**/*.js',
  '!source/chroma_ui/vendor/**/*.js',
  '!../ui-modules/**/*.js'
);

var options = minimist(process.argv.slice(2), { string: 'env' });
var isProduction = (options.env === 'production');

gulp.task('default', ['static', 'clean-static'], function buildApp () {
  var scripts = getJavaScripts()
    .pipe(plumber())
    .pipe(gulpIf(isProduction, annotate))
    .pipe(gulpIf(isProduction, iifeWrap))
    .pipe(gulpIf(isProduction, sourcemaps.init()))
    .pipe(gulpIf(isProduction, concat('built.js')))
    .pipe(gulpIf(isProduction, uglify({ compress: true, screw_ie8: true, mangle: true })))
    .pipe(gulpIf(isProduction, rev()))
    .pipe(gulpIf(isProduction, sourcemaps.write('.')))
    .pipe(gulp.dest('static/chroma_ui', { cwd: '../../chroma_ui' }));

  var lessFile = compileLess()
    .pipe(plumber())
    .pipe(gulpIf(isProduction, rev()))
    .pipe(gulpIf(isProduction, csso()))
    .pipe(gulp.dest('static/chroma_ui/styles', { cwd: '../../chroma_ui' }));

  return gulp.src(files.templates.server.index, { cwd: '../' })
    .pipe(plumber())
    .pipe(injector(lessFile))
    .pipe(injector(scripts))
    .pipe(gulp.dest('templates/new', { cwd: '../../chroma_ui' }));
});


/**
 * Watch files for changes.
 * Any source file change triggers a rebuild.
 */
gulp.task('watch', ['default'], function watcher () {
  var sourceFiles = files.js.source
    .concat(files.less.source)
    .concat(files.less.imports)
    .concat(files.assets.fonts)
    .concat(files.assets.images)
    .concat(files.templates.angular.source)
    .concat(files.templates.server.index);

  gulp.watch(sourceFiles, { cwd: '../' }, ['default']);
});

/*
 * Move static resources for distributable
 */
gulp.task('static', ['clean-static'], function staticBuild () {
  return gulp.src([files.assets.fonts, files.assets.images], { cwd: '../', base: '../source' })
    .pipe(gulp.dest('static', { cwd: '../../chroma_ui' }));
});

/**
 * Clean out the static dir
 * @param {Function} cb
 */
gulp.task('clean-static', function cleanStatic (cb) {
  del(['../../chroma_ui/static/chroma_ui/**/*'], { force: true }, cb);
});


/**
 * Runs code quality tools.
 */
gulp.task('quality', ['jscs', 'jshint']);

/**
 * Lint and report on files.
 */
gulp.task('jshint', function jsHint () {
  return gulp.src(qualityFiles, { cwd: '../' })
    .pipe(plumber())
    .pipe(cache('linting'))
    .pipe(jshint('../.jshintrc'))
    .pipe(jshint.reporter(stylish));
});

/**
 * Check JavaScript code style with jscs
 */
gulp.task('jscs', function jsCs () {
  return gulp.src(qualityFiles, { cwd: '../' })
    .pipe(plumber())
    .pipe(cache('codestylechecking'))
    .pipe(jscs('../.jscsrc'));
});

/**
 * Logs errors and ends the stream.
 * @param {Error} error
 */
function handleError (error) {
  /* jshint validthis: true */
  console.error(error);
  this.emit('end');
}

/**
 * Gets the JavaScript files.
 * @returns {Object}
 */
function getJavaScripts () {
  var primusClient = gulpPrimus().on('error', handleError);
  var javaScriptSourceFiles = gulp.src(files.js.source, { cwd: '../' });

  return streamqueue({ objectMode: true }, primusClient, javaScriptSourceFiles, compileTemplates())
    .on('error', handleError);
}

/**
 * Compiles Less files.
 * @returns {Object}
 */
function compileLess () {
  return gulp.src(files.less.imports, { cwd: '../' })
    .pipe(plumber())
    .pipe(less({
      relativeUrls: false,
      rootpath: '',
      paths: ['../source/chroma_ui/']
    }))
    .pipe(plumber.stop());
}

/**
 * Compiles templates.
 * @returns {Object}
 */
function compileTemplates () {
  return gulp.src(files.templates.angular.source, { cwd: '../' })
    .pipe(plumber())
    .pipe(minifyHtml({
      quotes: true,
      empty: true
    }))
    .pipe(ngHtml2Js({
      moduleName: 'iml',
      prefix: '/static/chroma_ui/',
      stripPrefix: 'source/chroma_ui'
    }))
    .pipe(plumber.stop());
}
