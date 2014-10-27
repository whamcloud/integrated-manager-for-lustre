'use strict';

var pipeline = require('../lib/pipeline');

describe('pipeline', function () {
  var pipe, request, response;

  beforeEach(function () {
    pipe = jasmine.createSpy('pipe');
    request = { bar: 'baz' };
    response = { foo: 'bar' };
  });

  it('should be a function', function () {
    expect(pipeline).toEqual(jasmine.any(Function));
  });

  it('should call the pipe with req, resp, and next', function () {
    pipe.and.callFake(function (req, resp, next) {
      next(req, resp);
    });

    pipeline([pipe], request, response);

    expect(pipe).toHaveBeenCalledOnceWith(request, response, jasmine.any(Function));
  });
});
