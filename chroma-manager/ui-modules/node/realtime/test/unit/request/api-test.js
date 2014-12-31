'use strict';
var rewire = require('rewire');
var api = rewire('../../../request/api');
var _ = require('lodash-mixins');

describe('api test', function () {
  var path, options, errorBuffer, λ,
    request, stream,
    revert, requestResult,
    addRequestInfo, addRequestInfoStream, buildOptions, opts, mask, through;

  beforeEach(function () {
    path = 'test/path';
    options = {};
    opts = {};
    requestResult = ['result'];

    stream = {
      through: jasmine.createSpy('through'),
      errors: jasmine.createSpy('errors')
    };

    stream.through.and.callFake(_.fidentity(stream));
    stream.errors.and.callFake(_.fidentity(stream));

    λ = jasmine.createSpy('highland').and.returnValue(stream);
    request = jasmine.createSpy('request').and.returnValue(requestResult);
    errorBuffer = jasmine.createSpy('errorBuffer');
    through = {
      toJson: jasmine.createSpy('toJson')
    };
    addRequestInfoStream = {};
    addRequestInfo = jasmine.createSpy('addRequestInfo').and.returnValue(addRequestInfoStream);
    buildOptions = jasmine.createSpy('buildOptions').and.returnValue(opts);
    mask = jasmine.createSpy('mask');

    revert = api.__set__({
      λ: λ,
      request: request,
      errorBuffer: errorBuffer,
      through: through,
      addRequestInfo: addRequestInfo,
      buildOptions: buildOptions,
      jsonMask: mask
    });
  });

  afterEach(function () {
    revert();
  });

  describe('with json', function () {
    beforeEach(function () {
      options = {
        json: { foo: 'bar' },
        jsonMask: 'p/a,z'
      };

      api(path, options);
    });

    it('should build a buffer from JSON', function () {
      expect(request.calls.mostRecent().args[1].toString()).toEqual('{"foo":"bar"}');
    });

    it('should not include the jsonMask in the options', function () {
      expect(buildOptions).toHaveBeenCalledOnceWith(path, {
        json: { foo: 'bar' }
      });
    });

    it('should call jsonMask with the mask', function () {
      expect(mask).toHaveBeenCalledOnceWith('p/a,z');
    });
  });

  describe('without json', function () {
    beforeEach(function () {
      api(path, options);
    });

    it('should call buildOptions with path and options', function () {
      expect(buildOptions).toHaveBeenCalledOnceWith(path, options);
    });

    it('should call request with options and buffer', function () {
      expect(request).toHaveBeenCalledOnceWith(opts, undefined);
    });

    it('should call highland with the result of request', function () {
      expect(λ).toHaveBeenCalledOnceWith(requestResult);
    });

    it('should call through with errorBuffer', function () {
      expect(stream.through).toHaveBeenCalledOnceWith(errorBuffer);
    });

    it('should call through with toJson', function () {
      expect(stream.through).toHaveBeenCalledOnceWith(through.toJson);
    });

    it('should call addRequestInfo with a path and options', function () {
      expect(addRequestInfo).toHaveBeenCalledOnceWith(path, options);
    });

    it('should call errors with addRequestInfo', function () {
      expect(stream.errors).toHaveBeenCalledOnceWith(addRequestInfoStream);
    });
  });
});
