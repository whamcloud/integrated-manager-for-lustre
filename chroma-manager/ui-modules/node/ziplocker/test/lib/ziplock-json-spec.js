'use strict';

var ziplockJsonModule = require('../../lib/ziplock-json').wiretree;
var _ = require('lodash-mixins');
var path = require('path');
var Promise = require('promise');

describe('ziplock JSON', function () {
  var getDependencyTree, config, fsThen, ziplockJsonData, promise, log, ziplockJson, process;

  beforeEach(function () {
    getDependencyTree = jasmine.createSpy('getDependencyTree');

    fsThen = {
      readFile: jasmine.createSpy('readFile'),
      writeFile: jasmine.createSpy('writeFile')
    };

    config = {
      ziplockPath: '/foo/ziplock.json',
      askQuestions: true
    };

    ziplockJsonData = {
      dependencies: {
        foo: '1.2.3'
      }
    };

    log = {
      write: jasmine.createSpy('write'),
      green: jasmine.createSpy('green'),
      diffObjects: jasmine.createSpy('diffObjects'),
      question: {
        yesOrNo: jasmine.createSpy('yesOrNo')
      }
    };

    process = {
      exit: jasmine.createSpy('exit')
    };

    ziplockJson = ziplockJsonModule(process, config, fsThen, getDependencyTree, log, _);
  });

  pit('should read a file', function () {
    fsThen.readFile.and.returnValue(Promise.resolve('{}'));

    return ziplockJson.readFile().then(function assertResponse () {
      expect(fsThen.readFile).toHaveBeenCalledWith('/foo/ziplock.json', { encoding : 'utf8' });
    });
  });

  describe('getting an existing file with matching data', function () {
    beforeEach(function () {
      fsThen.readFile.and.returnValue(Promise.resolve('{}'));
      getDependencyTree.and.returnValue(Promise.resolve({}));

      promise = ziplockJson.writeFile();
    });

    it('should read the ziplock file', function () {
      expect(fsThen.readFile)
        .toHaveBeenCalledWith(path.join(config.ziplockPath), { encoding: 'utf8' });
    });

    pit('should resolve file data if file exists', function () {
      return promise.then(function assertResponse (response) {
        expect(response).toEqual({});
      });
    });
  });

  describe('writing a new file', function () {
    beforeEach(function () {
      var error = new Error('ENOENT');
      error.code = 'ENOENT';

      fsThen.readFile.and.returnValue(Promise.reject(error));
      fsThen.writeFile.and.returnValue(Promise.resolve({}));
      getDependencyTree.and.returnValue(Promise.resolve({}));

      promise = ziplockJson.writeFile();
    });

    pit('should write a new ziplock file', function () {
      return promise.then(function assertFileWrite () {
        expect(fsThen.writeFile).toHaveBeenCalledWith(config.ziplockPath, '{}');
      });
    });

    pit('should return the file data', function () {
      return promise.then(function assertResponse (response) {
        expect(response).toEqual({});
      });
    });
  });

  pit('should re-throw the error if not ENOENT', function () {
    var error = new Error('Generic Error');
    error.code = 'EDUNNO';

    fsThen.readFile.and.returnValue(Promise.reject(error));

    return ziplockJson.writeFile().catch(function (reason) {
      expect(reason).toBe(error);
    });
  });

  describe('different trees', function () {
    beforeEach(function () {
      fsThen.readFile.and.returnValue(Promise.resolve('{}'));
      fsThen.writeFile.and.returnValue(Promise.resolve({}));
      getDependencyTree.and.returnValue(Promise.resolve({ foo: 'bar' }));
    });

    describe('say yes', function () {
      beforeEach(function () {
        log.question.yesOrNo.and.returnValue(Promise.resolve(true));
        promise = ziplockJson.writeFile();
      });

      pit('should diff the objects', function () {
        return promise.then(function assertResult () {
          expect(log.diffObjects).toHaveBeenCalled();
        });
      });

      pit('should write the file', function () {
        return promise.then(function assertResult () {
          expect(fsThen.writeFile).toHaveBeenCalledWith('/foo/ziplock.json', '{\n  "foo": "bar"\n}');
        });
      });

      pit('should return the JSON', function () {
        return promise.then(function assertResult (result) {
          expect(result).toEqual({foo: 'bar'});
        });
      });
    });

    describe('say no', function () {
      beforeEach(function () {
        log.question.yesOrNo.and.returnValue(Promise.resolve(false));
        promise = ziplockJson.writeFile();
      });

      pit('should exit the process', function () {
        return promise.then(function assertResult () {
          expect(process.exit).toHaveBeenCalledWith(0);
        });
      });
    });
  });
});
