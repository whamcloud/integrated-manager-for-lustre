'use strict';

var sinon = require('sinon'),
  streamFactory = require('../../stream');

require('jasmine-sinon');

describe('stream', function () {
  var Stream, stream, clock, logger;

  beforeEach(function () {
    logger = {
      error: sinon.spy()
    };

    Stream = streamFactory(logger);
    stream = new Stream();

    clock = sinon.useFakeTimers();
  });

  afterEach(function () {
    clock.restore();
  });

  it('should default to 10 seconds', function () {
    expect(stream.interval).toBe(10000);
  });

  it('should be configurable via constructor param', function () {
    var stream = new Stream(5000);

    expect(stream.interval).toBe(5000);
  });

  describe('start', function () {
    var cb;

    beforeEach(function () {
      cb = sinon.spy();

      stream.start(cb);
    });

    it('should call the callback', function () {
      expect(cb).toHaveBeenCalledOnce();
    });

    it('should call after the interval period', function () {
      clock.tick(10001);

      expect(cb).toHaveBeenCalledTwice();
    });

    it('should call with error if timer has already started', function () {
      stream.start(cb);

      expect(cb).toHaveBeenCalledWith({error: new Error('Already streaming')});
    });


    describe('stop', function () {
      beforeEach(function () {
        stream.stop();
      });

      it('should null the timer', function () {
        expect(stream.timer).toBeNull();
      });

      it('should clear the interval', function () {
        clock.tick(10001);

        expect(cb).toHaveBeenCalledOnce();
      });
    });
  });

});