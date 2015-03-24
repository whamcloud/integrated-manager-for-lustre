'use strict';
var rewire = require('rewire');
var bufferRequest = rewire('../buffer-request');
var _ = require('lodash-mixins');

describe('api test', function () {
  var path, options, errorBuffer, λ,
    requestStream, stream,
    revert, requestResult, response,
    addRequestInfo, addRequestInfoStream, buildOptions, opts, mask, through;

  beforeEach(function () {
    path = 'test/path';
    options = {};
    opts = {};
    requestResult = ['{"result": "result"}'];

    stream = {
      through: jasmine.createSpy('through'),
      errors: jasmine.createSpy('errors')
    };

    stream.through.and.callFake(function addResponseHeaders (fn) {
      if (fn && !fn.and) {
        var processedStream = {
          map: jasmine.createSpy('mapHeadersAndBody').and.callFake(function (mapHeadersAndBody) {
            return mapHeadersAndBody(JSON.parse(requestResult[0]));
          })
        };

        response = fn(processedStream);
      }

      return stream;
    });

    stream.errors.and.callFake(_.fidentity(stream));

    λ = jasmine.createSpy('highland').and.returnValue(stream);
    requestStream = jasmine.createSpy('requestStream').and.returnValue(requestResult);
    errorBuffer = jasmine.createSpy('errorBuffer');
    through = {
      toJson: jasmine.createSpy('toJson'),
      bufferString: jasmine.createSpy('bufferString')
    };
    addRequestInfoStream = {};
    addRequestInfo = jasmine.createSpy('addRequestInfo').and.returnValue(addRequestInfoStream);
    buildOptions = jasmine.createSpy('buildOptions').and.returnValue(opts);
    mask = jasmine.createSpy('mask').and.callFake(function () {
      requestResult.responseHeaders = {header: 'header'};
    });

    revert = bufferRequest.__set__({
      λ: λ,
      requestStream: requestStream,
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

      bufferRequest(path, options);
    });

    it('should build a buffer from JSON', function () {
      expect(requestStream.calls.mostRecent().args[1].toString()).toEqual('{"foo":"bar"}');
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
      bufferRequest(path, options);
    });

    it('should call buildOptions with path and options', function () {
      expect(buildOptions).toHaveBeenCalledOnceWith(path, options);
    });

    it('should call request with options and buffer', function () {
      expect(requestStream).toHaveBeenCalledOnceWith(opts, undefined);
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

    it('should call through.bufferString', function () {
      expect(stream.through).toHaveBeenCalledOnceWith(through.bufferString);
    });

    it('should setup the response to have headers and body properties', function () {
      expect(response).toEqual({
        headers: {header: 'header'},
        body: {result: 'result'}
      });
    });

    it('should call addRequestInfo with a path and options', function () {
      expect(addRequestInfo).toHaveBeenCalledOnceWith(path, options);
    });

    it('should call errors with addRequestInfo', function () {
      expect(stream.errors).toHaveBeenCalledOnceWith(addRequestInfoStream);
    });
  });
});
