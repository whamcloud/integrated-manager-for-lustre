'use strict';

var _ = require('lodash-mixins');
var rewire = require('rewire');
var addRequestInfo = rewire('../../../request/add-request-info');

describe('add request info', function () {
  var logger, path, options, err, push, revert;
  beforeEach(function () {
    logger = {
      child: jasmine.createSpy('child'),
      error: jasmine.createSpy('error')
    };

    logger.child.and.callFake(_.fidentity(logger));

    revert = addRequestInfo.__set__({ logger: logger });

    path = '/api/alert';
    options = { method: 'GET' };
    err = { message: 'error message' };
    push = jasmine.createSpy('push');

    addRequestInfo(path, options, err, push);
  });

  afterEach(function () {
    revert();
  });

  it('should log the path', function () {
    expect(logger.child).toHaveBeenCalledOnceWith({
      path: path,
      verb: options.method
    });
  });

  describe('errors', function () {
    var expectedError;
    beforeEach(function () {
      expectedError = {
        message: 'error message From GET request to /api/alert'
      };
    });

    it('should handle an error', function () {
      expect(logger.error).toHaveBeenCalledOnceWith(expectedError);
    });

    it('should push the error', function () {
      expect(push).toHaveBeenCalledOnceWith(expectedError);
    });
  });
});
