/*jshint node: true*/
'use strict';

/**
 * A wrapper that denodeify's the filesystem fs.readFile call
 * @param {Object} fs
 * @param {Promise} Promise
 * @returns {Object}
 */
exports.wiretree = function fsThenModule(fs, Promise) {
  return Promise.denodeify(fs.readFile);
};
