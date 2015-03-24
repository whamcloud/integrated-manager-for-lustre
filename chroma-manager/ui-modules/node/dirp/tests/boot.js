'use strict';

if (process.env.NODE_ENV === 'CI') {
  var KrustyJasmineReporter = require('krusty-jasmine-reporter');
  var junitReporter = new KrustyJasmineReporter.KrustyJasmineJUnitReporter({
      specTimer: new jasmine.Timer(),
      JUnitReportSavePath: process.env.SAVE_PATH || './',
      JUnitReportFilePrefix: process.env.FILE_PREFIX || 'dirp-results',
      JUnitReportSuiteName: 'Dirp Reports',
      JUnitReportPackageName: 'Dirp Reports'
    });

  jasmine.getEnv().addReporter(junitReporter);
}


