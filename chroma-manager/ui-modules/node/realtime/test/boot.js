'use strict';

require('jasmine-n-matchers');

var conf = require('../conf');

if (conf.get('RUNNER') === 'CI') {
  var krustyJasmineReporter = require('krusty-jasmine-reporter');

  var junitReporter = new krustyJasmineReporter.KrustyJasmineJUnitReporter({
    specTimer: new jasmine.Timer(),
    JUnitReportSavePath: process.env.SAVE_PATH || './',
    JUnitReportFilePrefix: process.env.FILE_PREFIX || 'realtime-results',
    JUnitReportSuiteName: 'Realtime Reports',
    JUnitReportPackageName: 'Realtime Reports'
  });

  jasmine.getEnv().addReporter(junitReporter);
}

jasmine.DEFAULT_TIMEOUT_INTERVAL = 30000;
