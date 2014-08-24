'use strict';

/**
 * Denodifies fs methods.
 * @param {Promise} Promise
 * @param {fs} fs
 * @returns {{readFile: Promise, writeFile: Promise}}
 */
exports.wiretree = function fsThenModule (Promise, fs) {
  return {
    readFile: Promise.denodeify(fs.readFile),
    writeFile: Promise.denodeify(fs.writeFile),
    copy: Promise.denodeify(fs.copy),
    /**
     * Given a path, tells if it exists.
     * @param path
     * @returns {Promise}
     */
    exists: function exists (path) {
      return new Promise(function handler (resolve) {
        fs.exists(path, resolve);
      });
    }
  };
};
