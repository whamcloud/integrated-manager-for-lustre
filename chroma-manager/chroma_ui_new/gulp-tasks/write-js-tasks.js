/*jslint node: true */

'use strict';

var files = require('../gulp-src-globs.json'),
  gulpWrite = require('../gulp-plugins/gulp-write');

module.exports = function (gulp) {
  gulp.task('write-js:dev', ['primus', 'static:dev'], writeJs.bind({
    src: files.js.source,
    cwd: 'static/**'
  }));

  gulp.task('write-js:build', ['compress'], writeJs.bind({
    src: 'static/chroma_ui/built-*.js'
  }));

  function writeJs () {
    /* jshint validthis: true */
    var src = this.cwd ? gulp.src(this.src, {cwd: this.cwd}) : gulp.src(this.src);

    return src
      .pipe(gulpWrite('templates_source/chroma_ui/base.html', 'writejs'))
      .pipe(gulp.dest('templates/chroma_ui'));
  }
};