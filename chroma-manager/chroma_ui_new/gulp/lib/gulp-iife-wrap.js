'use strict';

var format = require('util').format;
var λ = require('highland');

module.exports = λ.pipeline(function wrap (s) {
  return s.map(function iifeWrap (x) {
    if (x.path.indexOf('primus') === -1)
      x._contents = format('(function(){ %s }());', x._contents);

    return x;
  });
});
