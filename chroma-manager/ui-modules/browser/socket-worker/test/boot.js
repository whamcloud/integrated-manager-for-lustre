'use strict';

require('jasmine-n-matchers');

if (process.env.RUNNER === 'CI') {
  var krustyJasmineReporter = require('krusty-jasmine-reporter');

  var junitReporter = new krustyJasmineReporter.KrustyJasmineJUnitReporter({
    specTimer: new jasmine.Timer(),
    JUnitReportSavePath: process.env.SAVE_PATH || './',
    JUnitReportFilePrefix: process.env.FILE_PREFIX || 'socket-worker-results',
    JUnitReportSuiteName: 'Socket Worker Reports',
    JUnitReportPackageName: 'Socket Worker Reports'
  });

  jasmine.getEnv().addReporter(junitReporter);
}

jasmine.DEFAULT_TIMEOUT_INTERVAL = 30000;
