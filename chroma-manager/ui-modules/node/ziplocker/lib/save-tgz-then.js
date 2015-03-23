'use strict';

/**
 * Fetches a .tgz from the registry, expands it and saves it to disk.
 * @param {Promise} Promise
 * @param {Object} requests
 * @param {zlib} zlib
 * @param {tar} tar
 * @returns {Function}
 */
exports.wiretree = function saveTgzThenModule (Promise, requests, zlib, tar) {
  return function saveTgzThen (tgzPath, expandOpts) {
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
