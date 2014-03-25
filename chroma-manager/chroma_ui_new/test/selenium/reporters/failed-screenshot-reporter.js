'use strict';

var path = require('path');
var fs = require('fs');
var Reporter = require('./reporter');
var inherits = require('util').inherits;

/**
 * Saves a screenshot after each failed test.
 * @param {Object} options Configuration.
 * @constructor
 */
function FailedScreenshotReporter (options) {
  Reporter.call(this, options);
}

inherits(FailedScreenshotReporter, Reporter);

/**
 * Saves a screenshot after each failed test.
 * @param {Object} spec The spec to grab the description from.
 */
FailedScreenshotReporter.prototype.reportSpecResults = function reportSpecResults (spec) {
  var passed = jasmine.getEnv().currentSpec.results().passed();
  var failedScreenshotReporter = this;

  if (!passed) {
    browser.takeScreenshot().then(function tookScreenshot(png) {
      failedScreenshotReporter.buildPath(function gotPath(error, newPath) {
        if (error) throw error;

        var fileName = failedScreenshotReporter.buildFileName(spec, 'png');
        var fileNameAndPath = path.join(newPath, fileName);
        var stream = fs.createWriteStream(fileNameAndPath);

        var buf = new Buffer(png, 'base64');

        stream.write(buf);
        stream.end();

        console.log('Saving screenshot to:', fileNameAndPath);
      });
    });
  }
};

module.exports = FailedScreenshotReporter;