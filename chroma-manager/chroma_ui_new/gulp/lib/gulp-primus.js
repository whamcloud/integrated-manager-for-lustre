'use strict';

var File = require('gulp-util').File;
var getClientLib = require('../../../realtime/get-client-lib');
var from = require('from');

module.exports = function gulpPrimus () {
  return from(function fromStream () {
    var file = new File({
      path: 'chroma_ui/vendor/primus-client/primus.js',
      contents: new Buffer(getClientLib())
    });

    this.emit('data', file);
    this.emit('end');
  });
};
