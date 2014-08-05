'use strict';

/**
 * Wraps childProcess.exec in a promise.
 * @param {child_process} childProcess
 * @param {Promise} Promise
 * @returns {Function}
 */
exports.wiretree = function execThenModule (childProcess, Promise) {
  /**
   * Given a command, executes it in a child process.
   * @param {String} command
   * @returns {Promise}
   */
  return function execThen (command) {
    return new Promise(function handler (resolve, reject) {
      childProcess.exec(command, function executed (error, stdout, stderr) {
        if (error)
          reject(error);
        else
          resolve([stdout, stderr]);
      });
    });
  };
};
