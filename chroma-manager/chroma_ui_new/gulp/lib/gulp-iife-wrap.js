'use strict';

var format = require('util').format;
var λ = require('highland');

module.exports = function iifeWrap () {
  return λ.pipeline(function wrap (s) {
    return s.map(function iifeWrap (x) {
      if (x.annotation)
        x._contents = new Buffer(
          format('(function(){\n%s\n%s\n}());', x.annotation.strict ? '\'use strict\';' : '', x._contents)
        );

      return x;
    });
  });
};
