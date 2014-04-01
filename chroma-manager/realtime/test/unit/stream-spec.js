'use strict';

var streamFactory = require('../../stream'),
  Q = require('q');

describe('stream', function () {
  var Stream, deferred, timers, cb;

  beforeEach(function () {
    timers = {
      setTimeout: jasmine.createSpy('timers.setTimeout').andReturn({}),
      clearTimeout: jasmine.createSpy('timers.clearTimeout')
    };

    deferred = Q.defer();

    spyOn(Q, 'defer').andReturn(deferred);
    spyOn(Q.makePromise.prototype, 'progress').andCallThrough();
    spyOn(deferred, 'notify').andCallThrough();
    spyOn(deferred, 'resolve').andCallThrough();

    Stream = streamFactory(Q, timers);

    cb = jasmine.createSpy('callback');
  });

  it('should default to 10 seconds for polling', function () {
    var stream = new Stream();

    expect(stream.interval).toBe(10000);
  });

  it('should allow seconds to be configurable', function () {
    var seconds = 5000;

    var stream = new Stream(seconds);

    expect(stream.interval).toBe(seconds);
  });

  describe('start', function () {
    var stream;

    beforeEach(function () {
      stream = new Stream();
      stream.start(cb);
    });

    it('should setup a deferred on start', function () {
      expect(Q.defer).toHaveBeenCalledOnce();
    });

    it('should call the callback on progress', function () {
      expect(Q.makePromise.prototype.progress).toHaveBeenCalledOnceWith(jasmine.any(Function));
    });

    it('should notify the callback', function () {
      expect(deferred.notify).toHaveBeenCalledOnceWith(jasmine.any(Function));
    });

    it('should notify every 10 seconds', function () {
      var notifyLoop = deferred.notify.mostRecentCall.args[0];

      notifyLoop();

      expect(timers.setTimeout).toHaveBeenCalledOnceWith(jasmine.any(Function), 10000);
    });

    it('should return early if deferred is already defined', function () {
      stream.start(cb);

      expect(Q.defer).toHaveBeenCalledOnce();
    });

    it('should return early if timer is already defined', function () {
      stream.start(cb);

      expect(Q.defer).toHaveBeenCalledOnce();
    });

    it('should not notify if stream was stopped', function () {
      var notifyLoop = deferred.notify.mostRecentCall.args[0];

      notifyLoop();

      var notify = timers.setTimeout.mostRecentCall.args[0];

      stream.stop();

      function callNotify () {
        notify();
      }
      expect(callNotify).not.toThrow();
    });
  });

  describe('stop', function () {
    var stream;

    beforeEach(function () {
      stream = new Stream();
    });

    it('should not resolve a non-existent deferred', function () {
      stream.stop();
      expect(deferred.resolve).not.toHaveBeenCalledOnce();
    });

    it('should resolve the deferred on a started stream', function () {
      stream.start(cb);

      stream.stop();

      expect(deferred.resolve).toHaveBeenCalledOnce();
    });

    it('should not clearTimeout on a non-existent timer', function () {
      stream.stop();
      expect(timers.clearTimeout).not.toHaveBeenCalledOnce();
    });

    it('should clearTimeout on a started stream', function () {
      stream.start(cb);

      var notifyLoop = deferred.notify.mostRecentCall.args[0];

      notifyLoop();

      stream.stop();

      expect(timers.clearTimeout).toHaveBeenCalledOnce();
    });
  });
});