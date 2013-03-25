// Testacular configuration

// base path, that will be used to resolve files and exclude
basePath = '';

// list of files / patterns to load in the browser
files = [
  JASMINE,
  JASMINE_ADAPTER,
  'static/js/lib/lodash.custom.js',
  'static/js/lib/underscore-min.js',
  'static/js/lib/xdate.js',
  'static/js/lib/angular/angular.js',
  'static/js/lib/angular/angular-resource.js',
  'test/lib/angular-mocks.js',
  'static/js/util/**/*.js',
  'static/js/constants.js',
  'static/js/interceptors/*.js',
  'static/js/models/models_module.js',
  'static/js/models/*.js',
  'static/js/services/services_module.js',
  'static/js/services/*.js',
  'static/js/controllers/controller_module.js',
  'static/js/controllers/*.js',
  'test/mock/**/*.js',
  'test/spec/**/*.js'
];

// list of files to exclude
exclude = [];

// test results reporter to use
// possible values: dots, progress, junit, growl, coverage

reporter = ['dots'];

// web server port
port = 8080;

// cli runner port
runnerPort = 9100;

// enable / disable colors in the output (reporters and logs)
colors = true;

// level of logging
// possible values: LOG_DISABLE || LOG_ERROR || LOG_WARN || LOG_INFO || LOG_DEBUG
logLevel = LOG_INFO;

// enable / disable watching file and executing tests whenever any file changes
autoWatch = true;

// Start these browsers, currently available:
// - Chrome
// - ChromeCanary
// - Firefox
// - Opera
// - Safari
// - PhantomJS
browsers = ['Chrome', 'Safari', 'Firefox'];

// Continuous Integration mode
// if true, it capture browsers, run tests and exit
singleRun = false;
