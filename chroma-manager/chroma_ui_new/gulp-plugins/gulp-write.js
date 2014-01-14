/*jslint node: true */

'use strict';

var through = require('through'),
  format = require('util').format,
  fs = require('fs'),
  path = require('path'),
  gutil = require('gulp-util'),
  PluginError = gutil.PluginError,
  File = gutil.File,
  mime = require('mime');


var TYPES = {
  'application/javascript': format.bind(null, '<script type="text/javascript" src="%s"></script>'),
  'text/css': format.bind(null, '<link rel="stylesheet" media="screen" href="%s" />')
};

module.exports = function(filePath, search) {
  if (!filePath) throw new PluginError('gulp-write',  'Missing filePath option for gulp-write');
  if (!search) throw new PluginError('gulp-write', 'Missing search option for gulp-write');

  var buffer = [];

  return through(bufferScripts, endStream);

  function bufferScripts(file) {
    /* jshint validthis: true */

    if (file.isNull()) return; // ignore

    if (file.isStream()) return this.emit('error', new PluginError('gulp-write',  'Streaming not supported'));

    var trimmedFilePath = file.path
      .replace(process.cwd(), '')
      .replace(/^\/source\//, '/static/');

    var tag = TYPES[mime.lookup(file.path)](trimmedFilePath);

    buffer.push(tag);
  }

  function endStream(){
    /* jshint validthis: true */

    var stream = this;

    if (buffer.length === 0) return this.emit('end');

    var joinedContents = buffer.join(gutil.linefeed);

    // This could be streamed.
    // Not sure how to combine into a single stream.
    fs.readFile(path.resolve(process.cwd(), filePath), {encoding: 'utf8'}, function (err, data) {
      if(err) stream.emit('error', new PluginError('gulp-write-js',  err));

      var searchComment = format('<!-- %s -->', search),
        newContents = data.replace(searchComment, joinedContents),
        joinedFile = new File({
          path: path.basename(filePath),
          contents: new Buffer(newContents)
        });

      stream.emit('data', joinedFile);
      stream.emit('end');
    });
  }
};