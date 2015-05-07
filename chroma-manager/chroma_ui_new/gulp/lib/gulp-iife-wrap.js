'use strict';

var format = require('util').format;
var λ = require('highland');

module.exports = λ.pipeline(function wrap (s) {
  return s.map(function iifeWrap (x) {

    if (x.annotation)
      x._contents = format('(function(){\n%s\n%s\n}());', x.annotation.strict ? '\'use strict\';' : '', x._contents);

    return x;
  });
});
