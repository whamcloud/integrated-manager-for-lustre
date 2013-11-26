/* jshint node: true */

// Karma configuration
// Generated on Tue Aug 06 2013 14:33:22 GMT-0400 (EDT)

var util = require('util');

module.exports = function(config) {
  'use strict';

  function bound(format) {
    return util.format.bind(util, format);
  }

  var sourceDir = bound('source/chroma_ui/%s');
  var bowerDir = bound(sourceDir('bower_components/%s'));
  var vendorDir = bound(sourceDir('vendor/%s'));
  var imlDir = bound(sourceDir('iml/%s'));
  var commonDir = bound(sourceDir('common/%s'));
  var testDir = bound('test/%s');

  config.set({

    // base path, that will be used to resolve files and exclude
    basePath: '',


    // frameworks to use
    frameworks: ['jasmine'],


    // list of files / patterns to load in the browser
    files: [
      bowerDir('jasmine-stealth/index.js'),
      bowerDir('angular/angular.js'),
      bowerDir('angular-resource/angular-resource.js'),
      bowerDir('lodash/dist/lodash.js'),
      bowerDir('underscore-contrib/dist/underscore-contrib.js'),
      vendorDir('**/*.js'),
      commonDir('**/*-module.js'),
      commonDir('**/*.js'),
      imlDir('**/*-module.js'),
      imlDir('**/*.js'),
      bowerDir('angular-mocks/angular-mocks.js'),
      testDir('mocks/mock.js'),
      testDir('**/*-module.js'),
      testDir('fixtures/fixtures.js'),
      testDir('fixtures/**/*.js'),
      testDir('global-setup.js'),
      testDir('**/*.js'),
      testDir('templates/**/*.html')
    ],

    // list of files to exclude
    exclude: [
      imlDir('iml.js'),
      imlDir('router.js'),
      testDir('selenium/**/*')
    ],


    // test results reporter to use
    // possible values: 'dots', 'progress', 'junit', 'growl', 'coverage'
    reporters: ['dots'],

    // Only used if junit reporter activated (ex "--reporters junit" on the command line)
    junitReporter: {
      suite: 'karma-tests'
    },


    preprocessors: {
      '**/*.html': ['ng-html2js']
    },

    ngHtml2JsPreprocessor: {
      moduleName: 'templates',
      stripPrefix: 'test/templates/'
    },

    // web server port
    port: 9876,


    // enable / disable colors in the output (reporters and logs)
    colors: true,


    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    logLevel: config.LOG_INFO,


    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: false,


    // Start these browsers, currently available:
    // - Chrome
    // - ChromeCanary
    // - Firefox
    // - Opera
    // - Safari (only Mac)
    // - PhantomJS
    // - IE (only Windows)
    browsers: ['Chrome'],


    // If browser does not capture in given timeout [ms], kill it
    captureTimeout: 60000,


    // Continuous Integration mode
    // if true, it capture browsers, run tests and exit
    singleRun: false
  });
};
