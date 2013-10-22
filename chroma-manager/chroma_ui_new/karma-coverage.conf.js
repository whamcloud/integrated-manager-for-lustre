var baseConfig = require('./karma.conf.js'),
  _ = require('lodash');


module.exports = function(config) {
  'use strict';

  baseConfig(config);

  config.set({
    reporters: ['coverage'],

    preprocessors: _.extend({}, config.preprocessors, {
      'source/chroma_ui/!(vendor|bower_components)/**/*.js': ['coverage']
    }),

    // Configure coverage type location
    coverageReporter: {
      type: 'cobertura',
      dir: 'coverage/'
    }
  });
};
