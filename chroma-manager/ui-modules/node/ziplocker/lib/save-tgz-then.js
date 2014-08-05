'use strict';

/**
 * Fetches a .tgz from the registry, expands it and saves it to disk.
 * @param {Promise} Promise
 * @param {Object} requests
 * @param {zlib} zlib
 * @param {tar} tar
 * @param {util} util
 * @returns {Function}
 */
exports.wiretree = function saveTgzThenModule (Promise, requests, zlib, tar, util) {
  return function saveTgzThen (dependencyName, version, expandOpts) {
    var tgzPath = util.format('%s/-/%s-%s.tgz', dependencyName, dependencyName, version);

    return new Promise(function saveTgzToDir (resolve, reject) {
      requests.requestPipe(tgzPath)
        .on('error', reject)
        .pipe(zlib.createGunzip())
        .on('error', reject)
        .pipe(tar.Extract(expandOpts))
        .on('error', reject)
        .on('end', resolve);
    });
  };
};
