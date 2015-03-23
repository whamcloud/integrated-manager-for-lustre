'use strict';

/**
 * Resolves package.json from a .tar.gz file on the interwebs.
 * @param {Object} requests
 * @param {Function} Promise
 * @param {Object} zlib
 * @param {Object} tar
 * @returns {Function}
 */
exports.wiretree = function resolveFromTgzModule (requests, Promise, zlib, tar) {
  /**
   * Resolves package.json data from a URL
   * @param {String} url
   * @returns {Promise}
   */
  return function resolveFromTgz (url) {
    return new Promise(function resolver (resolve, reject) {
      requests.requestPipe(url)
        .on('error', reject)
        .pipe(zlib.createGunzip())
        .on('error', reject)
        .pipe(tar.Parse())
        .on('error', reject)
        .on('entry', function buildJson (e) {
          if (!(/package\.json$/).test(e.props.path))
            return;

          var data = '';

          e.on('data', function (c) {
            data += c.toString();
          });

          e.on('end', function () {
            resolve({
              response: JSON.parse(data),
              value: url
            });
          });
        });
    });
  };
};


