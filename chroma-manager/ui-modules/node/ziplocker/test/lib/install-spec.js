'use strict';

var installModule = require('../../lib/install').wiretree;
var wiretree = require('../../index');
var config = wiretree.get('config');
var treeClimber = wiretree.get('treeClimber');
var path = require('path');
var Promise = require('promise');
var format = require('util').format;

describe('install module', function () {
  var install, cprThen, execThen, ziplockJson, delThen, log, process, json, cwdModulesFormat;

  beforeEach(function () {
    json = {
      devDependencies: {
        baz: {
          version: '3.0.0',
          optionalDependencies: {
            bat: {
              version: '4.0.0'
            }
          }
        }
      },
      dependencies: {
        foo: {
          version: '1.0.0',
          optionalDependencies: {
            bar: {
              version: '2.0.0'
            }
          }
        },
        boom: {
          version: '2.3.0',
          optionalDependencies: {
            bam: {
              version: '9999.1'
            }
          }
        }
      }
    };

    config.ziplockDir = '/projects/chroma/chroma-externals';

    cprThen = jasmine.createSpy('createSpy').and.returnValue(Promise.resolve(''));
    execThen = jasmine.createSpy('execThen');

    ziplockJson = {
      readFile: jasmine.createSpy('readFile')
    };

    spyOn(treeClimber, 'climb').and.callThrough();

    delThen = jasmine.createSpy('delThen').and.returnValue(Promise.resolve(''));

    log = {
      write: jasmine.createSpy('write'),
      green: jasmine.createSpy('green'),
      yellow: jasmine.createSpy('yellow')
    };

    var cwd = '/projects/chroma/chroma-manager/ui-modules/node/stuff/';
    process = {
      cwd: jasmine.createSpy('cwd').and.returnValue(cwd)
    };
    /**
     * Formatting helper to add a path to cwd.
     * @param {String} path
     * @returns {String}
     */
    cwdModulesFormat = function cwdModulesFormat (path) {
      return format('%snode_modules%s', cwd, path || '');
    };

    install = installModule(cprThen, config, path, execThen, treeClimber, ziplockJson, Promise, delThen, log, process);
  });

  it('should return an object', function () {
    expect(install).toEqual({
      prod: jasmine.any(Function),
      dev: jasmine.any(Function)
    });
  });

  ['prod', 'dev'].forEach(function (mode) {
    describe('install ' + mode, function () {
      var promise;

      beforeEach(function () {
        execThen.and.callFake(function handleExec (command) {
          if (command === 'npm build ' + cwdModulesFormat('/boom/optionalDependencies/bam'))
            return Promise.reject(new Error('uh oh, this module requires Windows NT.'));

          return Promise.resolve([]);
        });

        ziplockJson.readFile.and.returnValue(Promise.resolve(JSON.stringify(json)));

        promise = install[mode]();
      });

      pit('should copy files from the zip dir to the modules dir', function () {
        return promise.then(function assertResults () {
          expect(cprThen).toHaveBeenCalledWith('/projects/chroma/chroma-externals/ziplocker/node_modules',
            cwdModulesFormat());
        });
      });

      pit('should rebuild files', function () {
        return promise.then(function assertResults () {
          expect(execThen).toHaveBeenCalledWith('npm rebuild');
        });
      });

      pit('should read the ziplock file', function () {
        return promise.then(function assertResults () {
          expect(ziplockJson.readFile).toHaveBeenCalled();
        });
      });

      pit('should climb the ziplock json tree', function () {
        return promise.then(function assertResults () {
          expect(treeClimber.climb).toHaveBeenCalledWith(json, jasmine.any(Function), '/');
        });
      });

      pit('should try to build an optional dependency', function () {
        return promise.then(function assertResults () {
          expect(execThen).toHaveBeenCalledWith('npm build ' + cwdModulesFormat('/foo/optionalDependencies/bar'));
        });
      });

      var possibleNegate = (mode === 'dev' ? ' not' : '');
      pit(format('should%s skip dev dependencies', possibleNegate), function () {
        return promise.then(function assertResults () {
          var expectation = expect(execThen);

          if (mode === 'prod')
            expectation = expectation.not;

          expectation.toHaveBeenCalledWith('npm build ' + cwdModulesFormat('/baz/optionalDependencies/bat'));
        });
      });

      pit('should move the optional dependency to node modules', function () {
        return promise.then(function assertResults () {
          expect(cprThen).toHaveBeenCalledWith(
            cwdModulesFormat('/foo/optionalDependencies/bar'),
            cwdModulesFormat('/foo/node_modules/bar')
          );
        });
      });

      pit('should delete the optionalDependency', function () {
        return promise.then(function assertResults () {
          expect(delThen).toHaveBeenCalledWith(
            cwdModulesFormat('/foo/optionalDependencies/bar')
          );
        });
      });

      pit('should reject failed builds', function () {
        return promise.then(function assertResults () {
          expect(log.write).toHaveBeenCalledWith('uh oh, this module requires Windows NT.');
        });
      });
    });
  });
});
