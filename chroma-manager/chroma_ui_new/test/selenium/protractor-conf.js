var manager = require('./util/manager');

exports.config = {
  seleniumServerJar: '/usr/local/opt/selenium-server-standalone/selenium-server-standalone-2.39.0.jar',

  specs: [
    'spec/global.js',
    'spec/**/*.js'
  ],

  capabilities: {
    browserName: 'chrome'
  },

  baseUrl: manager.server_http_url,

  jasmineNodeOpts: {
    showColors: true,
    defaultTimeoutInterval: 10000
  }
};
