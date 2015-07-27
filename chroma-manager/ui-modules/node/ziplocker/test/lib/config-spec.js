'use strict';

var configModule = require('../../lib/config').wiretree;
var path = require('path');

describe('config', function () {
  var config, process, configulator;

  beforeEach(function () {
    process = {
      env: {
        HTTP_PROXY: 'http://proxy-us.intel.com:911',
        ZIPLOCK_DIR: '/Users/iml/projects/chroma/chroma-externals'
      },
      cwd: jasmine.createSpy('cwd').and.returnValue('/Users/iml/projects/chroma/chroma-manager/ziplocker/')
    };

    spyOn(path, 'join').and.callThrough();

    configulator = jasmine.createSpy('configulator').and.callFake(function processConf (conf) {
      return conf.default;
    });

    config = configModule(process, path, configulator);
  });

  it('should call configulator with the correct config', function () {
    expect(configulator).toHaveBeenCalledWith({
      default: {
        FILE_TOKEN: 'file:',
        tarGzRegexp: /\.tar\.gz$/,
        registryUrl: 'https://registry.npmjs.org/',
        proxyUrl: process.env.HTTP_PROXY,
        ziplockDir: process.env.ZIPLOCK_DIR,
        packageName: 'ziplocker',
        ziplockPath: '/Users/iml/projects/chroma/chroma-manager/ziplocker/ziplock.json',
        DEP_TYPES: {
          DEPS: 'dependencies',
          OPTIONAL: 'optionalDependencies',
          DEV: 'devDependencies'
        },
        askQuestions: true
      },
      development: {},
      production: {}
    });
  });
});
