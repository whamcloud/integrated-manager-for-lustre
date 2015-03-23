'use strict';

/**
 * Writes dependencies to their commit location.
 * @param {Object} config
 * @param {Object} treeClimber
 * @param {path} path
 * @param {Function} saveTgzThen
 * @param {Function} saveRepoThen
 * @param {Object} log
 * @param {Object} fsThen
 * @param {process} process
 * @param {Object} semver
 * @param {Object} util
 * @returns {Function}
 */
exports.wiretree = function writeDependenciesModule (config, treeClimber, path, saveTgzThen,
                                                     saveRepoThen, log, fsThen, process, semver, util) {
  var replaceRegexp = new RegExp(config.DEP_TYPES.DEPS, 'g');

  /**
   * Climbs a ziplock.json file writing each dependency to it's specified spot in the tree.
   * @param {Object} json
   * @return Promise
   */
  return function writeDependencies (json) {
    var TREE_SEP = '/';

    return treeClimber.climbAsync(json, function visitor (key, value, fullPath) {
      var writePromise;
      var parts = fullPath.split(TREE_SEP);
      parts.pop();
      var normalizedPath = parts.join(TREE_SEP).replace(replaceRegexp, 'node_modules');
      fullPath = path.join(config.depPath, normalizedPath);

      var dependencyName = parts.pop();

      if (value.indexOf(config.FILE_TOKEN) !== -1) {
        var partialPath = value.replace(config.FILE_TOKEN, '');
        var resolvedPath = path.resolve(process.cwd(), partialPath);

        log.write(resolvedPath, fullPath);

        writePromise = fsThen.copy(resolvedPath, fullPath);
      } else if (semver.validRange(value)) {
        var tgzPath = util.format('%s%s/-/%s-%s.tgz', config.registryUrl, dependencyName, dependencyName, value);

        writePromise = saveTgzThen(tgzPath, {
          path: fullPath,
          strip: 1
        });
      } else if (config.tarGzRegexp.test(value)) {
        writePromise = saveTgzThen(value, {
          path: fullPath,
          strip: 1
        });
      } else {
        writePromise = saveRepoThen(value, fullPath);
      }

      return writePromise.then(function logSave () {
        log.write('Wrote', log.green(dependencyName), 'to', fullPath);
      });
    }, TREE_SEP)
      .then(function allDone (values) {
        log.write(log.green('Finished'), 'Wrote all dependencies');

        return values;
      });
  };
};
