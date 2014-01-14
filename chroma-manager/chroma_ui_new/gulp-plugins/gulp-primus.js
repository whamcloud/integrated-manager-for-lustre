/*jslint node: true */

'use strict';

var gutil = require('gulp-util'),
  PluginError = gutil.PluginError,
  File = require('gulp-util').File,
  from = require('from');

module.exports = function (requirePath) {
  if (!requirePath) throw new PluginError('gulp-primus',  'Missing requirePath option for gulp-primus');

  var generateLib = require(requirePath);

  return from(function fromStream() {
    var file = new File({
      path: 'primus.js',
      contents: new Buffer(generateLib())
    });

    this.emit('data', file);
    this.emit('end');
  });
};
