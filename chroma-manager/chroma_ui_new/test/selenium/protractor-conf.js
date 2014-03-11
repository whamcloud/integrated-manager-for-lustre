/*jslint node: true */

'use strict';

var manager = require('./util/manager');
var format = require('util').format;

exports.config = {
  seleniumServerJar: '/usr/local/opt/selenium-server-standalone/libexec/selenium-server-standalone-2.40.0.jar',
  seleniumArgs: ['-log', 'selenium_server.log'],
  chromeDriver: '/usr/local/bin/chromedriver',

  specs: [
    'spec/global.js',
    'spec/**/*.js'
  ],

  capabilities: {
    browserName: 'chrome',
    chromeOptions: {
      args: ['ignore-certificate-errors', 'no-proxy-server', 'enable-crash-reporter',
        'full-memory-crash-report', 'enable-logging=stderr', 'log-level=""', 'v=1000']
    },
    verbose: 'true',
    'log-path': 'chromedriver.log'
  },

  baseUrl: manager.server_http_url,

  onPrepare: function() {
    // Use jasmine-reporters junit reporter to create a results file consumable by Jenkins.
    require('jasmine-reporters');
    var reporter = new jasmine.JUnitXmlReporter('', true, false);

    global.browser.getCapabilities().then(function (capabilities) {
      var browserName = capabilities.caps_.browserName;

      // Lets get a more organized test report by putting all the results in "protractor-selenium-tests"
      var oldGetFullName = reporter.getFullName.bind(reporter);
      reporter.getFullName = function (suite, isFilename) {
        return format('protractor-selenium-tests.%s.%s',
          browserName,
          oldGetFullName(suite, isFilename)
        );
      };

      jasmine.getEnv().addReporter(reporter);
    });
  },

  jasmineNodeOpts: {
    showColors: true,
    isVerbose: true,
    defaultTimeoutInterval: 600000 // 10 minutes.
  }
};
