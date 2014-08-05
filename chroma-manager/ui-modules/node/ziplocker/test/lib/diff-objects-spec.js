'use strict';

var logDiffObjectsModule = require('../../lib/log-diff-objects').wiretree;

describe('Diff Objects', function () {
  var logDiffObjects, unfunkDiff, console;

  beforeEach(function () {
    console = {
      log: jasmine.createSpy('log')
    };

    unfunkDiff = {
      ansi: jasmine.createSpy('ansi').and.returnValue('diffed!')
    };

    logDiffObjects = logDiffObjectsModule(unfunkDiff, console);
  });

  it('should return a function', function () {
    expect(logDiffObjects).toEqual(jasmine.any(Function));
  });

  it('should diff two items in ansi mode, 80 chars', function () {
    var a = {};
    var b = {};

    logDiffObjects(a, b);

    expect(unfunkDiff.ansi).toHaveBeenCalledWith(a, b, 80);
  });

  it('should log the diff in the console', function () {
    var a = {};
    var b = {};

    logDiffObjects(a, b);

    expect(console.log).toHaveBeenCalledWith('diffed!');
  });
});
