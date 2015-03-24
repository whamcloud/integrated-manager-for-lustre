'use strict';

var λ = require('highland');
var errorBuffer = require('../error-buffer');
var _ = require('lodash-mixins');

describe('error buffer', function () {
  it('should pass through non-errors', function () {
    λ(['foo'])
      .through(errorBuffer)
      .each(function (x) {
        expect(x).toEqual('foo');
      });
  });

  it('should pass through stream errors', function () {
    λ([new StreamError(new Error('boom!'))])
      .through(errorBuffer)
      .errors(function (err) {
        expect(err).toEqual(new Error('boom!'));
      })
      .each(_.noop);
  });

  it('should buffer bad status codes', function () {
    var err = new Error();
    err.statusCode = 400;

    λ([
      new StreamError(err),
      'bo',
      'om',
      '!'
    ])
      .through(errorBuffer)
      .errors(function (err) {
        expect(err).toEqual(new Error('boom!'));
      })
      .each(_.noop);
  });

  function StreamError (err) {
    this.__HighlandStreamError__ = true;
    this.error = err;
  }
});
