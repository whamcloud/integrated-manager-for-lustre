'use strict';

require('jasmine-n-matchers');
if (process.env.RUNNER === 'CI') {
  var krustyJasmineReporter = require('krusty-jasmine-reporter');

  var junitReporter = new krustyJasmineReporter.KrustyJasmineJUnitReporter({
    specTimer: new jasmine.Timer(),
    JUnitReportSavePath: process.env.SAVE_PATH || './',
    JUnitReportFilePrefix: process.env.FILE_PREFIX || 'fp-results',
    JUnitReportSuiteName: 'FP Reports',
    JUnitReportPackageName: 'FP Reports'
  });

  jasmine.getEnv().addReporter(junitReporter);
}
