'use strict';

var fsThenModule = require('../../lib/fs-then').wiretree;

describe('fs then module', function () {
  var fsThen, Promise, fs;

  beforeEach(function () {
    Promise = {
      denodeify: jasmine.createSpy('denodeify')
        .and.returnValue(function denodeified () {})
    };

    fs = jasmine.createSpyObj('fs', ['readFile', 'writeFile']);

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

  it('should call Promise.denodeify with fs.readFile', function () {
    expect(Promise.denodeify).toHaveBeenCalledWith(fs.readFile);
  });

  it('should call Promise.denodeify with fs.writeFile', function () {
    expect(Promise.denodeify).toHaveBeenCalledWith(fs.writeFile);
  });
});
