'use strict';

var File = require('gulp-util').File;
var generateLib = require('../../../realtime/generate-lib');
var from = require('from');

module.exports = function gulpPrimus () {
  return from(function fromStream () {
    var file = new File({
      path: 'chroma_ui/vendor/primus-client/primus.js',
      contents: new Buffer(generateLib())
    });

    this.emit('data', file);
    this.emit('end');
  });
};
