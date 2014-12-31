'use strict';

var rewire = require('rewire');
var end = rewire('../../../../socket-router/middleware/end');

describe('end spec', function () {
  var logger, child, next, req, resp, revert, stream, onDestroy, debug;

  beforeEach(function () {
    child = {
      info: jasmine.createSpy('info')
    };

    debug = jasmine.createSpy('debug');

    logger = {
      child: jasmine.createSpy('child').and.returnValue({
        debug: debug
      })
    };

    revert = end.__set__('logger', logger);

    next = jasmine.createSpy('next');

    req = { matches: ['foo'] };

    resp = {
      socket: {
        once: jasmine.createSpy('once')
      }
    };

    stream = {
      destroy: jasmine.createSpy('destroy')
    };

    end(req, resp, stream, next);

    onDestroy = resp.socket.once.calls.mostRecent().args[1];
  });

  afterEach(function () {
    revert();
  });

  it('should create a log child', function () {
    expect(logger.child).toHaveBeenCalledOnceWith({
      path: 'foo'
    });
  });

  it('should call next with the request and response', function () {
    expect(next).toHaveBeenCalledOnceWith(req, resp);
  });

  it('should not call destroy if nil was seen', function () {
    stream._nil_seen = true;

    onDestroy();

    expect(stream.destroy).not.toHaveBeenCalled();
  });

  it('should not call destroy if stream was ended', function () {
    stream.ended = true;

    onDestroy();

    expect(stream.destroy).not.toHaveBeenCalled();
  });

  it('should not call destroy twice', function () {
    onDestroy();
    onDestroy();

    expect(stream.destroy).toHaveBeenCalledOnce();
  });

  it('should not call debug twice', function () {
    onDestroy();

    expect(debug).toHaveBeenCalledOnceWith(req, 'stream ended');
  });
});
