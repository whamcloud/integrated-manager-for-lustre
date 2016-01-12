// Testacular configuration

// list of files / patterns to load in the browser
module.exports = function(config) {
  config.set({

    basePath: '',

    frameworks: ['jasmine'],

    files: [
      'static/js/lib/underscore-min.js',
      'static/js/lib/lodash.custom.js',
      'static/js/lib/jquery.js',
      'static/js/lib/xdate.js',
      'static/js/lib/angular/angular.js',
      'static/js/lib/angular/angular-resource.js',
      'static/js/lib/angular/ui-bootstrap.js',
      'static/js/lib/highcharts.js',
      'test/lib/angular-mocks.js',
      'static/js/lib/sprintf/*.js',
      'static/js/app/help.js',
      'static/js/modules/**/*-module.js',
      'static/js/modules/**/*.js',
      'static/js/constants.js',
      'static/js/filters/filters_module.js',
      'static/js/filters/*.js',
      'static/js/interceptors/*_module.js',
      'static/js/interceptors/*.js',
      'static/js/models/models_module.js',
      'static/js/models/*.js',
      'static/js/services/services_module.js',
      'static/js/services/*.js',
      'static/js/controllers/controller_module.js',
      'static/js/controllers/**/*.js',
      'static/js/directives/directive_module.js',
      'static/js/directives/*.js',
      'static/js/chart_manager.js',
      'test/mocks/mock.js',
      'test/mocks/**/*.js',
      'test/mocks/register-mocks.js',
      'test/spec/**/*.js',
      'test/leak/**/*.js'
    ],

    // test results reporter to use
    // possible values: dots, progress, junit, growl, coverage

    reporters: ['dots'],

    junitReporter: {
      suite: 'karma-tests (old ui)'
    },

    port: 9876,

    // enable / disable colors in the output (reporters and logs)
    colors: true,

    // level of logging
    // possible values: LOG_DISABLE || LOG_ERROR || LOG_WARN || LOG_INFO || LOG_DEBUG
    logLevel: config.LOG_WARN,

    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: false,

    // Start these browsers, currently available:
    // - Chrome
    // - ChromeCanary
    // - Firefox
    // - Opera
    // - Safari
    // - PhantomJS
    browsers: ['Chrome', 'Firefox'],

    // Continuous Integration mode
    // if true, it capture browsers, run tests and exit
    singleRun: true
  });
};
