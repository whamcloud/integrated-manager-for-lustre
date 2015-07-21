'use strict';

var λ = require('highland');

var strict = { strict: true };

var annotate = λ.curry(function annotate (part, obj, x) {
  if (x.path.indexOf(part) !== -1) x.annotation = obj;

  return x;
});

module.exports = function () {
  return λ.pipeline(function getThroughStream (s) {
    return s
      .map(annotate('source/chroma_ui/common', strict))
      .map(annotate('source/chroma_ui/iml', strict));
  });
};
