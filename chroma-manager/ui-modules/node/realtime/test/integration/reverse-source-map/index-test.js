'use strict';

var reverseSourceMap = require('../../../reverse-source-map');
var clientError = require('../../integration/fixtures/client-error');

describe('reverse source map', function () {
  it('should reverse a trace', function (done) {
    reverseSourceMap(clientError().originalTrace.options.stack)
      .each(function (x) {
        expect(x).toEqual(clientError().reversedTrace.request.data.stack);
        done();
      });
  });
});
