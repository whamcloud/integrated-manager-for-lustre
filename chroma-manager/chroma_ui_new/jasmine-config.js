module.exports = {
  // An array of filename globs, relative to current dir.
  specs: ['./test/integration/*-spec.js'],
  // If true, display suite and spec names.
  isVerbose: true,
  // If true, print colors to the terminal.
  showColors: true,
  // If true, include stack traces in failures.
  includeStackTrace: true,
  // Time to wait in milliseconds before a test automatically fails
  defaultTimeoutInterval: 660000,
  // The name of the JUnit report
  JUnitReportSuiteName: 'Srcmap Generation Reports',
  // The name of the junit package
  JUnitReportPackageName: 'Srcmap Generation Reports'
};
