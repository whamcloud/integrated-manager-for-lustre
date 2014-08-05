'use strict';

/**
 * Resolves a dependency to package.json like info from the registry.
 * @param {Object} requests
 * @param {semver} semver
 * @returns {Function}
 */
exports.wiretree = function resolveFromRegistryModule (requests, semver) {
  /**
   * Resolves a dependency and it's max version from the registry.
   * @param {String} dependency
   * @param {String} version
   * @return {Object}
   */
  return function resolveFromRegistry (dependency, version) {
    return requests.requestThen(dependency)
      .then(function buildResponseObject (response) {
        var versions = Object.keys(response.body.versions);
        var maxVersion = semver.maxSatisfying(versions, version);

        return {
          response: response.body.versions[maxVersion],
          value: maxVersion
        };
      });
  };
};
