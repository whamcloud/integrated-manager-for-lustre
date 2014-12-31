'use strict';

var λ = require('highland');
var _ = require('lodash-mixins');
var toJson = require('../../../request/to-json');

describe('to JSON', function () {
  it('should parse a stream to JSON', function () {
    λ(['{', '"foo":"b', 'ar"}'])
      .through(toJson)
      .each(function (x) {
        expect(x).toEqual({ foo: 'bar' });
      });
  });

  it('should throw on invalid JSON', function () {
    λ(['{', '"foo":"bar"'])
      .through(toJson)
      .errors(function (err) {
        expect(err).toEqual(new Error('Could not parse {"foo":"bar" to JSON.'));
      })
      .each(_.noop);
  });
});
