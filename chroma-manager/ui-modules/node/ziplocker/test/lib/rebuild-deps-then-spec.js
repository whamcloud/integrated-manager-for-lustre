'use strict';

var rebuildDepsThenModule = require('../../lib/rebuild-deps-then').wiretree;
var Promise = require('promise');

describe('Rebuild deps then', function () {
  var rebuildDepsThen, childProcess, console, rebuild;

  beforeEach(function () {
    rebuild = {
      stdout: {
        on: jasmine.createSpy('on')
      },
      stderr: {
        on: jasmine.createSpy('on')
      },
      on: jasmine.createSpy('on')
    };

    childProcess = {
      spawn: jasmine.createSpy('spawn').and.returnValue(rebuild)
    };

    console = {
      log: jasmine.createSpy('log')
    };

    rebuildDepsThen = rebuildDepsThenModule(Promise, childProcess, console);
  });

  it('should be a function', function () {
    expect(rebuildDepsThen).toEqual(jasmine.any(Function));
  });

  it('should return a promise', function () {
    expect(rebuildDepsThen()).toEqual(jasmine.any(Promise));
  });

  describe('rebuilding', function () {
    var promise;

    beforeEach(function () {
      promise = rebuildDepsThen();
    });

    it('should spawn a process', function () {
      expect(childProcess.spawn).toHaveBeenCalledWith('npm', ['rebuild']);
    });

    it('should listen on stdout', function () {
      expect(rebuild.stdout.on).toHaveBeenCalledWith('data', jasmine.any(Function));
    });

    it('should listen on stderr', function () {
      expect(rebuild.stderr.on).toHaveBeenCalledWith('data', jasmine.any(Function));
    });

    it('should listen on close', function () {
      expect(rebuild.on).toHaveBeenCalledWith('close', jasmine.any(Function));
    });

    describe('closing', function () {
      var handler;

      beforeEach(function () {
        handler = rebuild.on.calls.mostRecent().args[1];
      });

      pit('should resolve on a 0 code', function () {
        handler(0);

        return promise.then(function assertCode (code) {
          expect(code).toEqual(0);
        });
      });

      pit('should reject on a non 0 code', function () {
        handler(1);

        return promise.catch(function assertError (err) {
          expect(err).toEqual(jasmine.any(Error));
        });
      });
    });
  });
});
