'use strict';

/**
 * Extension over chalk to write the app identifier
 * and bundle up console base utilities.
 * @param {console} console
 * @param {Object} chalk
 * @param {Object} logDiffObjects
 * @param {Object} question
 * @returns {Object}
 */
exports.wiretree = function logModule (console, chalk, logDiffObjects, question) {
  var log = Object.create(chalk);

  /**
   * Writes a ziplock message to the console.
   */
  log.write = function write () {
    var args = [].slice.call(arguments, 0);
    args.unshift(chalk.blue('ziplock'));

    console.log.apply(null, args);
  };

  log.diffObjects = logDiffObjects;

  log.question = question;

  return log;
};
