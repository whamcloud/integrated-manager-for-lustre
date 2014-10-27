'use strict';

var loopFactory = require('../../loop-factory').wiretree;
var _ = require('lodash-mixins');

describe('loop', function () {
  var loop, timers, handler, finish;

  beforeEach(function () {
    timers = {
      setTimeout: jasmine.createSpy('setTimeout').andReturn(692),
      clearTimeout: jasmine.createSpy('clearTimeout')
    };

    handler = jasmine.createSpy('handler');

    loop = loopFactory(timers, _);

    finish = loop(handler, 1000);
  });

  it('should return a finish function', function () {
    expect(finish).toEqual(jasmine.any(Function));
  });

  it('should invoke handler on start', function () {
    expect(handler).toHaveBeenCalledOnceWith(jasmine.any(Function));
  });

  it('should invoke timeout after first next call', function () {
    var next = handler.mostRecentCall.args[0];
    next();

    expect(timers.setTimeout).toHaveBeenCalledOnceWith(jasmine.any(Function), 1000);
  });

  describe('finishing the loop', function () {
    beforeEach(function () {
      var next = handler.mostRecentCall.args[0];
      next();

      finish();
    });

    it('should clear the timeout when calling finish', function () {
      expect(timers.clearTimeout).toHaveBeenCalledOnce();
    });

    it('should not call handler', function () {
      timers.setTimeout.mostRecentCall.args[0]();

      handler.mostRecentCall.args[0]();

      expect(timers.setTimeout).toHaveBeenCalledOnce();
    });
  });
});
