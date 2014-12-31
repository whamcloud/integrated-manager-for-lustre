'use strict';

var PassThrough = require('stream').PassThrough;
var path = require('path');
var del = require('del');
var gulp = require('gulp');
var cache = require('gulp-cached');
var remember = require('gulp-remember');
var less = require('gulp-less');
var csso = require('gulp-csso');
var mergeStream = require('merge-stream');
var order = require('gulp-order');
var injector = require('gulp-inject');
var jscs = require('gulp-jscs');
var jshint = require('gulp-jshint');
var stylish = require('jshint-stylish');
var minifyHtml = require('gulp-minify-html');
var ngHtml2Js = require('gulp-ng-html2js');
var plumber = require('gulp-plumber');
var rev = require('gulp-rev');
var sourcemaps = require('gulp-sourcemaps');
var concat = require('gulp-concat');
var uglify = require('gulp-uglify');
var iifeWrap = require('./lib/gulp-iife-wrap');
var annotate = require('./lib/gulp-annotate');
var ngAnnotate = require('gulp-ng-annotate');
var clone = require('gulp-clone');
var glob2base = require('glob2base');
var Glob = require('glob').Glob;
var anymatch = require('anymatch');
var files = require('./gulp-src-globs.json');
var fp = require('fp');

var writeToDest = fp.curry(2, gulp.dest)(fp.__, { cwd: '../../chroma_ui' });
var writeToStatic = writeToDest.bind(null, 'static/chroma_ui');
var getSource = fp.curry(2, gulp.src)(fp.__, { cwd: '../' });

function buildJs () {
  return getSource(files.js.source)
    .pipe(plumber())
    .pipe(cache('scripts'))
    .pipe(ngAnnotate({ add: true }))
    .pipe(annotate())
    .pipe(iifeWrap())
    .pipe(plumber.stop());
}

var buildAssets = getSource.bind(null, [files.assets.fonts, files.assets.images]);

function buildLess () {
  return getSource(files.less.imports)
    .pipe(plumber())
    .pipe(less({
      relativeUrls: false,
      rootpath: '',
      paths: ['../source/chroma_ui/']
    }))
    .pipe(plumber.stop());
}

function buildTemplates () {
  return getSource(files.templates.angular.source)
    .pipe(plumber())
    .pipe(cache('scripts'))
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

var toStatic = fp.curry(3, function toStatic (type, filepath, file) {
  return injector.transform.html[type]('/static/chroma_ui/' + file.relative);
});

function injectFiles (jsStream, lessStream) {
  return getSource(files.templates.server.index)
    .pipe(plumber())
    .pipe(injector(lessStream, {
      transform: toStatic('css')
    }))
    .pipe(injector(jsStream, {
      transform: toStatic('js')
    }))
    .pipe(writeToDest('templates/new'))
    .pipe(plumber.stop());
}

var orderJsFiles = order.bind(null, files.js.source, { base: '../' });

gulp.task('clean', function clean (cb) {
  del(['../../chroma_ui/static/chroma_ui/**/*'], { force: true }, cb);
});

gulp.task('dev', ['clean'], function devTask () {
  var jsStream = buildJs();
  var templatesStream = buildTemplates();
  var lessStream = buildLess();
  var assetsStream = buildAssets();

  var merged = mergeStream(jsStream, templatesStream);

  var statics = mergeStream(
    merged.pipe(clone()),
    lessStream.pipe(clone()),
    assetsStream
  ).pipe(writeToStatic());

  var ordered = merged
    .pipe(orderJsFiles())
    .pipe(remember('scripts'));

  var indexStream = injectFiles(ordered, lessStream);

  return mergeStream(indexStream, statics);
});

gulp.task('prod', ['clean'], function prodTask () {
  var jsStream = buildJs();
  var templatesStream = buildTemplates();
  var assetsStream = buildAssets();

  var lessStream = buildLess()
    .pipe(plumber())
    .pipe(rev())
    .pipe(csso())
    .pipe(plumber.stop());

  var merged = mergeStream(jsStream, templatesStream)
    .pipe(plumber())
    .pipe(orderJsFiles())
    .pipe(sourcemaps.init())
    .pipe(concat('built.js'))
    .pipe(uglify({ compress: true, screw_ie8: true, mangle: true }))
    .pipe(rev())
    .pipe(sourcemaps.write('.'))
    .pipe(plumber.stop());

  var statics = mergeStream(
    merged.pipe(clone()),
    lessStream.pipe(clone()),
    assetsStream
  ).pipe(writeToStatic());

  var indexStream = injectFiles(merged, lessStream);

  return mergeStream(indexStream, statics);
});

var lessSrc = gulp.src.bind(null, files.less.imports, {
  read: false,
  cwd: '../'
});

gulp.task('incremental-js', function () {
  var jsFiles = buildJs();

  jsFiles
    .pipe(clone())
    .pipe(writeToStatic());

  jsFiles = jsFiles
    .pipe(remember('scripts'))
    .pipe(orderJsFiles());

  return injectFiles(jsFiles, lessSrc());
});

gulp.task('incremental-templates', function () {
  var jsFiles = buildTemplates();

  jsFiles
    .pipe(clone())
    .pipe(writeToStatic());

  jsFiles = jsFiles
    .pipe(remember('scripts'))
    .pipe(orderJsFiles());

  return injectFiles(jsFiles, lessSrc());
});

gulp.task('incremental-less', function () {
  var lessFile = buildLess();

  var p = new PassThrough();

  var jsFiles = p
    .pipe(remember('scripts'));

  var written = mergeStream(jsFiles.pipe(clone()), lessFile.pipe(clone()))
    .pipe(writeToStatic());

  jsFiles = jsFiles
    .pipe(orderJsFiles());

  var s = injectFiles(jsFiles, lessFile);

  p.end();

  return mergeStream(s, written);
});

gulp.task('incremental-assets', function () {
  return buildAssets()
    .pipe(writeToStatic());
});

var getDest = fp.curry(3, function getDest (globs, filePath, opts) {
  var sourcePath = path.relative(opts.cwd, filePath);
  var index = anymatch(globs, sourcePath, true);
  var glob = globs[index];
  var fileBase = path.resolve(opts.cwd, glob2base(new Glob(glob)));
  var basePath = path.resolve(opts.destCwd);
  var commonPath = path.relative(fileBase, filePath);

  return path.resolve(basePath, commonPath);
});

gulp.task('watch', ['dev'], function () {
  var watchCwd = fp.curry(3, gulp.watch.bind(gulp))(fp.__, {
    cwd: '../'
  });
  var toDest = getDest(fp.__, fp.__, {
    cwd: '../',
    destCwd: '../../chroma_ui/static/chroma_ui'
  });

  var deleted = fp.eqFn(fp.identity, fp.lensProp('type'), 'deleted');
  var ifDeleted = fp.flow(toArray, fp.invokeMethod('concat', fp.__, [deleted]), fp.and);

  function toArray (x) { return [x]; }

  var jsWatch = watchCwd(files.js.source, ['incremental-js']);
  jsWatch.on('change', ifDeleted(function handleChange (ev) {
    delete cache.caches.scripts[ev.path];
    remember.forget('scripts', ev.path);

    var dest = toDest(files.js.source, ev.path);
    del.sync(dest, { force: true });
  }));

  var replaceHtml = fp.invokeMethod('replace', [/\.html$/, '.js']);
  var templateWatch = watchCwd(files.templates.angular.source, ['incremental-templates']);
  templateWatch.on('change', ifDeleted(function handleChange (ev) {
    var path = replaceHtml(ev.path);

    delete cache.caches.scripts[ev.path];
    remember.forget('scripts', path);

    var toDestAndReplace = fp.flow(toDest(files.templates.angular.source), replaceHtml);
    del.sync(toDestAndReplace(path), { force: true });
  }));

  var lessFiles = files.less.source
    .concat(files.less.imports);
  watchCwd(lessFiles, ['incremental-less']);

  var assets = [files.assets.fonts]
    .concat(files.assets.images);
  var assetWatch = watchCwd(assets, ['incremental-assets']);
  assetWatch.on('change', ifDeleted(function handleChange (ev) {
    var dest = toDest(assets, ev.path);
    del.sync(dest, { force: true });
  }));

  watchCwd(files.templates.server.index, ['incremental-templates']);
});

var qualitySource = getSource.bind(null, files.js.source.concat(
  'test/spec/**/*.js',
  'test/mock/**/*.js',
  'test/*.js',
  '!source/chroma_ui/bower_components/**/*.js',
  '!source/chroma_ui/vendor/**/*.js',
  '!../ui-modules/**/*.js'
));

gulp.task('quality', ['jscs', 'jshint']);

gulp.task('jshint', function jsHint () {
  return qualitySource()
    .pipe(plumber())
    .pipe(jshint())
    .pipe(jshint.reporter(stylish))
    .pipe(plumber.stop());
});

gulp.task('jscs', function jsCs () {
  return qualitySource()
    .pipe(plumber())
    .pipe(jscs('../.jscsrc'))
    .pipe(plumber.stop());
});
