var manager = require('./util/manager');

exports.config = {
  seleniumServerJar: '/usr/local/opt/selenium-server-standalone/selenium-server-standalone-2.39.0.jar',
  seleniumArgs: ['-log', 'selenium_server.log'],

  specs: [
    'spec/global.js',
    'spec/**/*.js'
  ],

  capabilities: {
    browserName: 'chrome',
    chromeOptions: {
        args: ['ignore-certificate-errors', 'no-proxy-server', 'enable-crash-reporter', 'full-memory-crash-report', 'enable-logging=stderr', 'log-level=""', 'v=1000']
    },
    verbose: 'true',
    'log-path': 'chromedriver.log'
  },

  baseUrl: manager.server_http_url,

  onPrepare: function() {
    // Use jasmine-reporters junit reporter to create a results file consumable by Jenkins.
    require('jasmine-reporters');
    var reporter = new jasmine.JUnitXmlReporter('', true, false);

    // Lets get a more organized test report by puting all the results in "protractor-selenium-tests"
    reporter.getFullNameForSpec = reporter.getFullName;
    reporter.browserName = this.capabilities.browserName;
    reporter.getFullName = function (suite, isFilename) {
      return 'protractor-selenium-tests.' + this.browserName + '.' + this.getFullNameForSpec(suite, isFilename);
    }

    jasmine.getEnv().addReporter(reporter);
  },

  jasmineNodeOpts: {
    showColors: true,
    isVerbose: true,
    defaultTimeoutInterval: 10000
  }
};
