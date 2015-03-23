'use strict';

var writeDependenciesModule = require('../../lib/write-dependencies').wiretree;
var treeClimber = require('tree-climber');
var path = require('path');
var Promise = require('promise');
var semver = require('semver');
var config = require('../../index').get('config');
var util = require('util');

describe('write dependencies', function () {
  var writeDependencies, saveTgzThen, saveRepoThen,
    log, promise, fsThen, process;

  beforeEach(function () {
    config.ziplockDir = '/projects/chroma/chroma-externals';

    saveTgzThen = jasmine.createSpy('saveTgzThen').and.returnValue(Promise.resolve(''));
    saveRepoThen = jasmine.createSpy('saveRepoThen').and.returnValue(Promise.resolve(''));

    process = {
      cwd: jasmine.createSpy('cwd').and.returnValue('/projects/chroma/chroma-manager/ui-modules/node/stuff/')
    };

    log = {
      write: jasmine.createSpy('write'),
      green: jasmine.createSpy('green')
    };

    fsThen = {
      copy: jasmine.createSpy('copy').and.returnValue(Promise.resolve())
    };

    spyOn(treeClimber, 'climbAsync').and.callThrough();

    writeDependencies = writeDependenciesModule(config, treeClimber, path, saveTgzThen,
      saveRepoThen, log, fsThen, process, semver, util);
  });

  describe('climbing a tree', function () {
    var json;

    beforeEach(function () {
      json = {
        dependencies: {
          'foo-bar': {
            version: 'https://foobar.com/foo-bar.1.0.0.tar.gz'
          },
          'primus-emitter': {
            version: '2.0.5'
          },
          dotty: {
            version: '0.0.2'
          },
          'coffee-script-redux': {
            version: 'git+https://github.com/michaelficarra/\
CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3'
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
          },
          'bar-foo': {
            version: 'https://foobar.com/bar-foo.2.0.0.tar.gz'
          }
        }
      };

      promise = writeDependencies(json);
    });

    it('should invoke treeClimber.climbAsync', function () {
      expect(treeClimber.climbAsync).toHaveBeenCalledWith(json, jasmine.any(Function), '/');
    });

    pit('should invoke saveTgzThen for tar.gz url dependencies', function () {
      return promise.then(function () {
        expect(saveTgzThen).toHaveBeenCalledWith(
          'https://foobar.com/foo-bar.1.0.0.tar.gz',
          {
            path: config.depPath + '/node_modules/foo-bar',
            strip: 1
          });
      });
    });

    pit('should invoke saveTgzThen for tar.gz url devDependencies', function () {
      return promise.then(function () {
        expect(saveTgzThen).toHaveBeenCalledWith(
          'https://foobar.com/bar-foo.2.0.0.tar.gz',
          {
            path: config.depPath + '/devDependencies/bar-foo',
            strip: 1
          });
      });
    });


    pit('should invoke saveTgzThen for dependencies', function () {
      return promise.then(function () {
        expect(saveTgzThen).toHaveBeenCalledWith(
          'https://registry.npmjs.org/primus-emitter/-/primus-emitter-2.0.5.tgz',
          {
            path : config.depPath + '/node_modules/primus-emitter',
            strip : 1
          });
      });
    });

    pit('should invoke saveTgzThen for devDependencies', function () {
      return promise.then(function () {
        expect(saveTgzThen).toHaveBeenCalledWith(
          'https://registry.npmjs.org/jasmine-n-matchers/-/jasmine-n-matchers-0.0.3.tgz',
          {
            path: config.depPath + '/devDependencies/jasmine-n-matchers',
            strip: 1
          });
      });
    });

    pit('should copy files', function () {
      return promise.then(function assertCall () {
        expect(fsThen.copy).toHaveBeenCalledWith('/projects/chroma/chroma-manager/ui-modules/node/promise-it',
          '/projects/chroma/chroma-externals/ziplocker/devDependencies/promise-it');
      });
    });

    pit('should save repos', function () {
      return promise.then(function assertCall () {
        expect(saveRepoThen).toHaveBeenCalledWith(
          'git+https://github.com/michaelficarra/CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3',
          '/projects/chroma/chroma-externals/ziplocker/node_modules/coffee-script-redux'
        );
      });
    });
  });
});
