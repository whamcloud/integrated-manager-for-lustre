'use strict';

exports.wiretree = function parseGithubUrlModule (Promise) {
  var prefix = /^git.*\:\/\//;

  /**
   * Tries to parse an npm dependency GitHub url.
   * Resolves with parsed url or rejects if url cannot
   * be parsed.
   * @param {String} url
   * @returns {Promise}
   */
  return function parseGithubUrl (url) {
    return new Promise(function handler (resolve, reject) {
      var parts = url
        .replace(prefix, '')
        .replace('github.com/', '')
        .split('#');

      if (parts.length !== 2)
        reject(new Error(url + ' does not appear to be a valid github url'));

      resolve({
        path: parts[0],
        commitIsh: parts[1]
      });
    });
  };
};
