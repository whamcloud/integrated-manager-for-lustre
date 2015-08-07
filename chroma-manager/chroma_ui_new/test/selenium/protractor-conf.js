'use strict';

var manager = require('./util/manager');
var format = require('util').format;

exports.config = {
  seleniumServerJar: '/usr/local/opt/selenium-server-standalone/libexec/selenium-server-standalone-2.47.1.jar',
  seleniumArgs: ['-log', 'selenium_server.log'],
  chromeDriver: '/usr/local/bin/chromedriver',

  specs: ['spec/**/*.js'],

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

  onPrepare: function onPrepare () {
    // Use jasmine-reporters junit reporter to create a results file consumable by Jenkins.
    require('jasmine-reporters');

    var ConsoleReporter = require('./reporters/console-reporter');
    var FailedScreenshotReporter = require('./reporters/failed-screenshot-reporter');
    var junitXmlReporter = new jasmine.JUnitXmlReporter('', true, false);

    browser.getCapabilities().then(function (capabilities) {
      var browserName = capabilities.caps_.browserName;

      // Lets get a more organized test report by putting all the results in "protractor-selenium-tests"
      var oldGetFullName = junitXmlReporter.getFullName.bind(junitXmlReporter);
      junitXmlReporter.getFullName = function (suite, isFilename) {
        return format('protractor-selenium-tests.%s.%s',
          browserName,
          oldGetFullName(suite, isFilename)
        );
      };

      jasmine.getEnv().addReporter(junitXmlReporter);
      jasmine.getEnv().addReporter(new ConsoleReporter({
        prepend: browserName,
        showDate: true,
        extraPath: 'protractor-console-logs'
      }));
      jasmine.getEnv().addReporter(new FailedScreenshotReporter({
        prepend: browserName,
        showDate: true,
        extraPath: 'failed-screen-shots'
      }));
    });
  },
  jasmineNodeOpts: {
    showColors: true,
    isVerbose: true,
    showTiming: true,
    includeStackTrace: true,
    defaultTimeoutInterval: manager.waitTimes.long
  }
};
