'use strict';

var fsThenModule = require('../../lib/fs-then').wiretree;

describe('fs then module', function () {
  var fsThen, Promise, fs;

  beforeEach(function () {
    Promise = jasmine.createSpy('Promise').and.returnValue({});
    Promise.denodeify = jasmine.createSpy('denodeify')
      .and.returnValue(function denodeified () {});

    fs = jasmine.createSpyObj('fs', ['readFile', 'writeFile', 'exists']);

    fsThen = fsThenModule(Promise, fs);
  });

  it('should return an object', function () {
    expect(fsThen).toEqual(jasmine.any(Object));
  });

  it('should have a readFile function', function () {
    expect(fsThen.readFile).toEqual(jasmine.any(Function));
  });

  it('should have a writeFile function', function () {
    expect(fsThen.writeFile).toEqual(jasmine.any(Function));
  });

  it('should have an exists function', function () {
    expect(fsThen.exists).toEqual(jasmine.any(Function));
  });

  it('should have a copy function', function () {
    expect(fsThen.copy).toEqual(jasmine.any(Function));
  });

  it('should call Promise.denodeify with fs.readFile', function () {
    expect(Promise.denodeify).toHaveBeenCalledWith(fs.readFile);
  });

  it('should call Promise.denodeify with fs.writeFile', function () {
    expect(Promise.denodeify).toHaveBeenCalledWith(fs.writeFile);
  });

  describe('exists', function () {
    var promise, path, handler, resolve;

    beforeEach(function () {
      path = '/foo';

      promise = fsThen.exists(path);

      handler = Promise.calls.mostRecent().args[0];
      resolve = jasmine.createSpy('resolve');

      handler(resolve);
    });

    it('should return a new promise', function () {
      expect(promise).toEqual(jasmine.any(Object));
    });

    it('should call fs.exists', function () {
      expect(fs.exists).toHaveBeenCalledWith(path, jasmine.any(Function));
    });

    it('should resolve with value', function () {
      fs.exists.calls.mostRecent().args[1](true);

      expect(resolve).toHaveBeenCalledWith(true);
    });
  });
});
