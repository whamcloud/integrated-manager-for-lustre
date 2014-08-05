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
    writeFile: Promise.denodeify(fs.writeFile)
  };
};
