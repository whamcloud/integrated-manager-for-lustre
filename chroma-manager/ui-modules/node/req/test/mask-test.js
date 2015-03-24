'use strict';

var rewire = require('rewire');
var mask = rewire('../mask');
var λ = require('highland');
var _ = require('lodash-mixins');

describe('through', function () {
  var theMask, jsonMask, revert;
  beforeEach(function () {
    theMask = 'a/p,z';
    jsonMask = jasmine.createSpy('jsonMask');

    revert = mask.__set__({
      jsonMask: jsonMask
    });
  });

  afterEach(function () {
    revert();
  });

  describe('with a mask', function () {
    var streamData, theMask, maskedData, highlandStream;
    beforeEach(function () {
      streamData = {
        key: 'value',
        key2: 'value'
      };
      theMask = 'key';
      maskedData = {key: 'value'};

      jsonMask.and.returnValue(maskedData);

      highlandStream = λ([streamData])
        .through(mask(theMask));
    });

    it('should call json-mask with the stream data and the mask', function (done) {
      highlandStream
        .each(function () {
          expect(jsonMask).toHaveBeenCalledOnceWith(streamData, theMask);
          done();
        });
    });

    it('should receive the masked data', function (done) {
      highlandStream
        .each(function (data) {
          expect(data).toEqual(maskedData);
          done();
        });
    });

    describe('that returns null', function () {
      var spy;
      beforeEach(function () {
        jsonMask.and.returnValue(null);

        spy = jasmine.createSpy('spy');
        highlandStream
          .errors(_.unary(spy))
          .each(_.noop);
      });

      it('should throw an error', function () {
          expect(spy).toHaveBeenCalledOnceWith(new Error('The json mask did not match the response and as a\
 result returned null. Examine the mask: "key"'));
      });

      it('should have a status code of 400', function () {
        expect(spy.calls.mostRecent().args[0].statusCode).toEqual(400);
      });
    });
  });

  describe('without a mask', function () {
    var streamData, highlandStream;
    beforeEach(function () {
      streamData = {
        key: 'value',
        key2: 'value'
      };

      highlandStream = λ([streamData])
        .through(mask(undefined));
    });

    it('should return the whole object', function (done) {
      highlandStream
        .each(function (data) {
          expect(data).toEqual(streamData);
          done();
        });
    });

    it('should not call json-mask', function (done) {
      highlandStream
        .each(function () {
          expect(jsonMask).not.toHaveBeenCalled();
          done();
        });
    });
  });
});
