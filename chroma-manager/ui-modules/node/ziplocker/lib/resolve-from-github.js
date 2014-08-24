'use strict';

/**
 * Resolves module info from github
 * @param {Object} requests
 * @param {Function} util
 * @param {Function} parseGithubUrl
 * @returns {Function}
 */
exports.wiretree = function resolveFromGithubModule (requests, util, parseGithubUrl) {
  /**
   * Resolves package.json data from GitHub
   * for GitHub based dependencies
   * @param {String} url
   * @returns {Promise}
   */
  return function resolveFromGithub (url) {
    return parseGithubUrl(url)
      .then(function getRawUrl (parsed) {
        return util.format(
          'https://raw.githubusercontent.com/%s/%s/package.json',
          parsed.path.replace('.git', ''),
          parsed.commitIsh
        );
      })
      .then(requests.requestThen)
      .then(function buildResponseObject (response) {
        return {
          response: response.body,
          value: url
        };
      });
  };
};


