'use strict';

var getDependencyTree = require('../../lib/get-dependency-tree').wiretree;
var Promise = require('promise');
var config = require('../../index').get('config');

describe('dependency tree', function () {
  var packageJson, promise, log, resolveFromFs, resolveFromRegistry;

  beforeEach(function () {
    packageJson = {
      dependencies: {
        foo: '^0.0.1',
        bar: '~1.2.3',
        bim: 'file://../bim/'
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

    var dependencyTree = getDependencyTree(packageJson, Promise, log, config, resolveFromFs, resolveFromRegistry);
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
