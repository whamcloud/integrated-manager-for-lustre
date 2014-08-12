'use strict';

module.exports = {
  // An array of filename globs, relative to current dir.
  specs: ['./test/*.spec.js'],
  isVerbose: true,
  showColors: true,
  includeStackTrace: true,
  defaultTimeoutInterval: 5000,
  JUnitReportSuiteName: 'Sourcemap Reverse Reports',
  JUnitReportPackageName: 'Sourcemap Reverse Reports'
};
