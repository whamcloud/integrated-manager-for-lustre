/*jshint node: true*/
'use strict';

module.exports = {
  // An array of filenames, relative to current dir. These will be
  // executed, as well as any tests added with addSpecs()
  specs: ['test/**/*-spec.js'],
  // If true, display suite and spec names.
  isVerbose: true,
  // If true, print colors to the terminal.
  showColors: true,
  // If true, include stack traces in failures.
  includeStackTrace: true,
  // Time to wait in milliseconds before a test automatically fails
  defaultTimeoutInterval: 5000,
  // The name of the JUnit report
  JUnitReportSuiteName: 'Stub Daddy Reports',
  // The name of the junit package
  JUnitReportPackageName: 'Stub Daddy Reports'
};
