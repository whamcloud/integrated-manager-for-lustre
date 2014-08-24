'use strict';

var getDependencyTree = require('../../lib/get-dependency-tree').wiretree;
var Promise = require('promise');
var semver = require('semver');
var config = require('../../index').get('config');

describe('dependency tree', function () {
  var packageJson, promise, log, resolveFromFs, resolveFromRegistry, resolveFromGithub;

  beforeEach(function () {
    packageJson = {
      dependencies: {
        foo: '^0.0.1',
        bar: '~1.2.3',
        bim: 'file://../bim/',
        'coffee-script-redux': 'git+https://github.com/michaelficarra/\
CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3'
      },
      optionalDependencies: {
        baz: '~3.4.7'
      },
      devDependencies: {
        bip: '^1.1.1'
      }
    };

    resolveFromFs = jasmine.createSpy('resolveFromFs').and.returnValue(Promise.resolve({
      response: {},
      value: 'file://../bim/'
    }));

    resolveFromGithub = jasmine.createSpy('resolveFromGithub').and.returnValue(Promise.resolve({
      response: {
        dependencies: {
          foo: '^0.0.1'
        }
      },
      value: 'git+https://github.com/michaelficarra/CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3'
    }));

    resolveFromRegistry = jasmine.createSpy('resolveFromRegistry').and.callFake(function (dependency, dependencyValue) {
      var responseObjects = {
        'foo^0.0.1': {
          response: {},
          value: '0.0.1'
        },
        'bar~1.2.3': {
          response: {
            dependencies: {
              bap: '^3.2.1'
            },
            devDependencies: {
              bip: '^2.1.1'
            }
          },
          value: '1.2.4'
        },
        'baz~3.4.7': {
          response: {},
          value: '3.4.8'
        },
        'bap^3.2.1': {
          response: {},
          value: '3.2.2'
        },
        'bip^2.1.1': {
          response: {},
          value: '2.1.1'
        },
        'bip^1.1.1': {
          response: {},
          value: '1.1.2'
        }
      };

      return Promise.resolve(responseObjects[dependency + dependencyValue]);
    });

    log = {
      write: jasmine.createSpy('write'),
      green: jasmine.createSpy('green')
    };

    var dependencyTree = getDependencyTree(packageJson, Promise, log, semver, config,
      resolveFromFs, resolveFromRegistry, resolveFromGithub);
    promise = dependencyTree();
  });

  it('should return a promise', function () {
    expect(promise).toEqual(jasmine.any(Promise));
  });

  it('should lookup foo', function () {
    expect(resolveFromRegistry).toHaveBeenCalledWith('foo', '^0.0.1');
  });

  it('should lookup bar', function () {
    expect(resolveFromRegistry).toHaveBeenCalledWith('bar', '~1.2.3');
  });

  it('should lookup coffeescript redux', function () {
    expect(resolveFromGithub).toHaveBeenCalledWith(
      'git+https://github.com/michaelficarra/CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3'
    );
  });

  pit('should return a ziplock object', function () {
    return promise.then(function checkResponse(ziplock) {
      expect(ziplock).toEqual({
        dependencies: {
          foo: {
            version: '0.0.1'
          },
          bar: {
            version: '1.2.4',
            dependencies: {
              bap: {
                version: '3.2.2'
              }
            }
          },
          bim: {
            version: 'file://../bim/'
          },
          'coffee-script-redux': {
            version: 'git+https://github.com/michaelficarra/\
CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3',
            dependencies: {
              foo: {
                version: '0.0.1'
              }
            }
          }
        },
        optionalDependencies: {
          baz: {
            version: '3.4.8'
          }
        },
        devDependencies: {
          bip: {
            version: '1.1.2'
          }
        }
      });
    });
  });
});
