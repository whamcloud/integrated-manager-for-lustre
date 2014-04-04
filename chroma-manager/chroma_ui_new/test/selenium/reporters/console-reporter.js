'use strict';

var fs = require('fs');
var path = require('path');
var Reporter = require('./reporter');
var inherits = require('util').inherits;

/**
 * Saves browser console output to a file per-test.
 * @param {Object} options Configuration.
 * @constructor
 */
function ConsoleReporter(options) {
  Reporter.call(this, options);
}

inherits(ConsoleReporter, Reporter);

/**
 * Saves browser console output to file after each test.
 * @param {Object} spec The spec to grab the description from.
 */
ConsoleReporter.prototype.reportSpecResults = function reportSpecResults (spec) {
  var consoleReporter = this;

  browser.manage().logs().get('browser').then(function gotLogs(browserLog) {
    consoleReporter.buildPath(function gotPath(error, newPath) {
      if (error) throw error;

      var fileName = consoleReporter.buildFileName(spec, 'json');
      var fileNameAndPath = path.join(newPath, fileName);

      fs.writeFile(fileNameAndPath, JSON.stringify(browserLog, null, 2), function wroteConsoleLog(error) {
        if (error) throw error;

        console.log('Saving console output to:', fileNameAndPath);
      });
    });
  });
};

module.exports = ConsoleReporter;