'use strict';

/**
 * Denodifies cpr.
 * @param {cpr} cpr
 * @param {Promise} Promise
 * @returns {Promise}
 */
exports.wiretree = function cprThenModule (cpr, Promise) {
  return Promise.denodeify(cpr);
};
