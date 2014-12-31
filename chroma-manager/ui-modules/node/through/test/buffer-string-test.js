'use strict';

var λ = require('highland');
var bufferString = require('../../../request/buffer-string');

describe('buffer string', function () {
  it('should work with a single chunk', function () {
    λ(['foo'])
      .through(bufferString)
      .each(function (x) {
        expect(x).toEqual('foo');
      });
  });

  it('should work with multiple chunks', function () {
    λ([
      new Buffer('f'),
      new Buffer('o'),
      new Buffer('o'),
      new Buffer('!')
    ])
      .through(bufferString)
      .each(function (x) {
        expect(x).toEqual('foo!');
      });
  });

  it('should not buffer an empty stream', function () {
    var spy = jasmine.createSpy('spy');

    λ([])
      .through(bufferString)
      .each(spy);

    expect(spy).not.toHaveBeenCalledOnce();
  });
});
