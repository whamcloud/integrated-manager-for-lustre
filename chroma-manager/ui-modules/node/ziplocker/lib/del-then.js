'use strict';

/**
 * Denodifies del.
 * @param {Function} del
 * @param {Promise} Promise
 * @returns {Promise}
 */
exports.wiretree = function (del, Promise) {
  return Promise.denodeify(del);
};
