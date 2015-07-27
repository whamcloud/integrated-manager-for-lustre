'use strict';

var resolveFromFsModule = require('../../lib/resolve-from-fs').wiretree;
var path = require('path');
var Promise = require('promise');

describe('resolve from fs', function () {
  var resolveFromFs, config, fsThen, process;

  beforeEach(function () {
    config = {
      FILE_TOKEN: 'file:'
    };

    fsThen = {
      readFile: jasmine.createSpy('readFile')
        .and.returnValue(Promise.resolve('{}'))
    };

    process = {
      cwd: jasmine.createSpy('cwd').and.returnValue('/bar/bat/')
    };

    resolveFromFs = resolveFromFsModule(fsThen, path, process, config);
  });

  it('should return a function', function () {
    expect(resolveFromFs).toEqual(jasmine.any(Function));
  });

  describe('calling with a file path', function () {
    var filePath, promise;

    beforeEach(function () {
      filePath = 'file:foo/bar';
      promise = resolveFromFs(filePath, '/bar/bat');
    });

    it('should read the package.json', function () {
      expect(fsThen.readFile).toHaveBeenCalledWith('/bar/bat/foo/bar/package.json', 'utf8');
    });

    pit('should return a responseObject', function () {
      return promise.then(function assertResponse (responseObject) {
        expect(responseObject).toEqual({
          response : {},
          value : 'file:foo/bar',
          newPath : '/bar/bat/foo/bar'
        });
      });
    });
  });
});
