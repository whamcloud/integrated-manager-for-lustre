'use strict';

require('jasmine-n-matchers');

module.exports = {
  // An array of filename globs, relative to current dir.
  specs: ['./test/**/*-spec.js'],
  isVerbose: true,
  showColors: true,
  includeStackTrace: true,
  defaultTimeoutInterval: 5000,
  JUnitReportSuiteName: 'Socket Router Reports',
  JUnitReportPackageName: 'Socket Router Reports'
};
