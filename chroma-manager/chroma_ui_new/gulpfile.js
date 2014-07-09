/*jslint node: true */

'use strict';

var gulp = require('gulp');
var gulpPrimus = require('./gulp-plugins/gulp-primus');
var jshint = require('gulp-jshint');
var jscs = require('gulp-jscs');
var stylish = require('jshint-stylish');
var files = require('./gulp-src-globs.json');
var uglify = require('gulp-uglify');
var concat = require('gulp-concat');
var rev = require('gulp-rev');
var replace = require('gulp-replace');
var minifyHtml = require('gulp-minify-html');
var ngHtml2Js = require('gulp-ng-html2js');
var injector = require('gulp-inject');
var less = require('gulp-less');
var csso = require('gulp-csso');
var cache = require('gulp-cached');
var streamqueue = require('streamqueue');
var del = require('del');
var gutil = require('gulp-util');

var qualityFiles = files.js.source.concat(
  'test/spec/**/*.js',
  'test/mock/**/*.js',
  'test/*.js',
  '!source/chroma_ui/bower_components/**/*.js',
  '!source/chroma_ui/vendor/**/*.js'
);

/**
 * Lint and report on files.
 */
gulp.task('jshint', function jsHint () {
  return gulp.src(qualityFiles)
    .pipe(cache('linting'))
    .pipe(jshint('.jshintrc'))
    .pipe(jshint.reporter(stylish));
});

/**
 * Check JavaScript code style with jscs
 * and our .jscsrc file.
 * @TODO: Waiting on fix for get/set es5:
 * https://github.com/mdevils/node-jscs/pull/336
 *  "disallowSpaceAfterObjectKeys": true,
 */
gulp.task('jscs', function jsCs () {
  return gulp.src(qualityFiles)
    .pipe(cache('codestylechecking'))
    .pipe(jscs('.jscsrc').on('error', function handleError (err) {
      this.emit('end');
      gutil.log(err.message);
    }));
});

/*
 * Runs code quality tools.
 */
gulp.task('quality', ['jscs', 'jshint']);

/*
 * Injects JS and CSS files for loading in base.html.
 */
gulp.task('inject:dev', ['static:dev', 'clean-static', 'copy-templates'], function injectDev () {
  var staticJSGlobs = files.js.source.map(function rewritePrefix (file) {
    return file.replace(/^source/, 'static');
  });
  var jsStream = gulp.src(staticJSGlobs, {
    read: false
  });
  var cssStream = compileLess()
    .pipe(gulp.dest('static/chroma_ui/styles'));

  var stream = streamqueue({ objectMode: true })
    .queue(cssStream)
    .queue(generatePrimusClientLib)
    .queue(jsStream)
    .done();

  return gulp.src('templates_source/chroma_ui/base.html')
    .pipe(injector(stream))
    .pipe(gulp.dest('templates/chroma_ui'));
});

/*
 * Copy templates over.
 */
gulp.task('copy-templates', ['clean-templates'], function copyTemplates () {
  return gulp.src([
    'templates_source/chroma_ui/**/*.html',
    '!templates_source/chroma_ui/base.html'
  ])
    .pipe(gulp.dest('templates/chroma_ui'));
});

/*
 * Clean out templates directory
 */
gulp.task('clean-templates', function cleanTemplates (cb) {
  del(['templates/**'], cb);
});

/*
 * Move static resources for development
 */
gulp.task('static:dev', ['clean-static'], function staticDev () {
  return gulp.src('source/chroma_ui/**/*.{html,js,png,woff,ttf,svg,ico}')
    .pipe(gulp.dest('static/chroma_ui'));
});

/*
 * Move static resources for distributable
 */
gulp.task('static:build', ['clean-static'], function staticDev () {
  return gulp.src('source/chroma_ui/**/*.{png,woff,ttf,svg,ico}')
    .pipe(gulp.dest('static/chroma_ui'));
});

/*
 * Clean out static dir.
 */
gulp.task('clean-static', function cleanStatic (cb) {
  del(['static/chroma_ui/**/*'], cb);
});

/*
 * Build out the distributable GUI.
 * - Concat and compress js and less
 * - Rev files so they can be perma-cached.
 * - rewrite the base tag to point at the built ui.
 */
gulp.task('build', ['copy-templates', 'static:build'], function builder () {
  var jsStream = compressor();
  var cssStream = compileLess()
    .pipe(csso())
    .pipe(rev())
    .pipe(gulp.dest('static/chroma_ui/styles'));

  var stream = streamqueue({ objectMode: true })
    .queue(cssStream)
    .queue(jsStream)
    .done();

  return gulp.src('templates_source/chroma_ui/base.html')
    .pipe(injector(stream))
    .pipe(replace(/(<base href=").+(" \/>)/, '$1/ui/$2'))
    .pipe(gulp.dest('templates/new', {
      cwd: '../chroma_ui'
    }));
});

/**
 * Watch files for changes.
 * - Watches .less files and compiles.
 * - Watches other static files and moves to the correct dir.
 * - Runs quality checks on changed files.
 */
gulp.task('watch', function watcher () {
  var sourceFiles = files.js.source.concat(files.less.source);
  gulp.watch(sourceFiles, ['inject:dev']);

  gulp.watch(qualityFiles, ['quality']);

  gulp.watch([
    'source/chroma_ui/**/*.{html,js,png,woff,ttf,svg,ico}',
    '!source/chroma_ui/bower_components/**'
  ], ['static:dev']);

  gulp.watch('templates_source/**/*.html', ['copy-templates']);
});

/*
 * The default task.
 * - Compiles less
 * - Injects CSS and JS files into base.html
 * - Watches files for changes and reruns tasks.
 */
gulp.task('default', ['watch', 'quality', 'inject:dev']);

/**
 * Concats and uglifies JS / Templates.
 * @return {Object} A stream.
 */
function compressor () {
  var templateFiles = compileTemplates();
  var primusClientLib = generatePrimusClientLib();

  return streamqueue({
      objectMode: true
    },
    primusClientLib,
    gulp.src(files.js.source),
    templateFiles
  )
    .pipe(concat('built.js'))
    .pipe(uglify({
      compress: {
        drop_debugger: true,
        drop_console: true
      }
    }))
    .pipe(rev())
    .pipe(gulp.dest('static/chroma_ui'));
}

/**
 * Compiles LESS file to CSS.
 * @returns {Object} Returns a stream.
 */
function compileLess () {
  return gulp.src(files.less.imports)
    .pipe(less({
      relativeUrls: false,
      rootpath: '',
      paths: ['source/chroma_ui/']
    }));
}

/**
 * Compiles Angular templates to JS.
 * @returns {Object} Returns a stream.
 */
function compileTemplates () {
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
    }));
}

/**
 * Writes the generated primus client lib.
 * @returns {Object} Returns a stream.
 */
function generatePrimusClientLib () {
  return gulpPrimus('../../realtime/generate-lib')
    .pipe(gulp.dest('static/chroma_ui/vendor/primus-client'));
}
