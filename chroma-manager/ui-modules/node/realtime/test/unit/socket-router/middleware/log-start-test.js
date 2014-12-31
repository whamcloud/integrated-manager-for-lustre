'use strict';

var rewire = require('rewire');
var logStart = rewire('../../../../socket-router/middleware/log-start');

describe('log start', function () {
  var logger, revert, child, next, req, resp;

  beforeEach(function () {
    child = {
      info: jasmine.createSpy('info'),
      debug: jasmine.createSpy('debug')
    };

    logger = {
      child: jasmine.createSpy('child').and.returnValue(child)
    };

    revert = logStart.__set__('logger', logger);

    req = { matches: ['foo'] };

    resp = {};

    next = jasmine.createSpy('next');

    logStart(req, resp, next);
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
});
