'use strict';

/**
 * Outputs the difference of two objects to the console.
 * @param {Object} unfunkDiff
 * @param {console} console
 * @returns {Function}
 */
exports.wiretree = function logDiffObjectsModule (unfunkDiff, console) {
  return function diffObjects (a, b) {
    console.log(unfunkDiff.ansi(a, b, 80));
  };
};
