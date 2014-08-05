'use strict';

var writeDependenciesModule = require('../../lib/write-dependencies').wiretree;
var treeClimber = require('tree-climber');
var path = require('path');
var Promise = require('promise');
var config = require('../../index').get('config');

describe('write dependencies', function () {
  var writeDependencies, saveTgzThen, log, promise, cprThen, process;

  beforeEach(function () {
    config.ziplockDir = '/projects/chroma/chroma-externals';

    saveTgzThen = jasmine.createSpy('saveTgzThen').and.returnValue(Promise.resolve(''));
    cprThen = jasmine.createSpy('cprThen').and.returnValue(Promise.resolve(''));

    process = {
      cwd: jasmine.createSpy('cwd').and.returnValue('/projects/chroma/chroma-manager/ui-modules/node/stuff/')
    };

    log = {
      write: jasmine.createSpy('write'),
      green: jasmine.createSpy('green')
    };

    spyOn(treeClimber, 'climbAsync').and.callThrough();

    writeDependencies = writeDependenciesModule(config, treeClimber, path, saveTgzThen, log, cprThen, process);
  });

  describe('climbing a tree', function () {
    var json;

    beforeEach(function () {
      json = {
        dependencies: {
          'primus-emitter': {
            version: '2.0.5'
          },
          dotty: {
            version: '0.0.2'
          }
        },
        devDependencies: {
          'jasmine-n-matchers': {
            version: '0.0.3'
          },
          'jasmine-object-containing': {
            version: '0.0.2'
          },
          'jasmine-stealth': {
            version: '0.0.15',
            dependencies: {
              'coffee-script': {
                version: '1.6.3'
              },
              minijasminenode: {
                version: '0.2.7'
              }
            }
          },
          'promise-it': {
            version: 'file://../promise-it'
          }
        }
      };

      promise = writeDependencies(json);
    });

    it('should invoke treeClimber.climbAsync', function () {
      expect(treeClimber.climbAsync).toHaveBeenCalledWith(json, jasmine.any(Function), '/');
    });

    pit('should invoke saveTgzThen for dependencies', function () {
      return promise.then(function () {
        expect(saveTgzThen).toHaveBeenCalledWith( 'primus-emitter', '2.0.5', {
          path : config.depPath + '/node_modules/primus-emitter',
          strip : 1
        });
      });
    });

    pit('should invoke saveTgzThen for devDependencies', function () {
      return promise.then(function () {
        expect(saveTgzThen).toHaveBeenCalledWith('jasmine-n-matchers', '0.0.3', {
          path: config.depPath + '/devDependencies/jasmine-n-matchers',
          strip: 1
        });
      });
    });

    pit('should invoke cprThen for files', function () {
      return promise.then(function assertCall () {
        expect(cprThen).toHaveBeenCalledWith('/projects/chroma/chroma-manager/ui-modules/node/promise-it',
          '/projects/chroma/chroma-externals/ziplocker/devDependencies/promise-it');
      });
    });
  });
});
