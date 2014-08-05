'use strict';

/**
 * Writes dependencies to their commit location.
 * @param {Object} config
 * @param {Object} treeClimber
 * @param {path} path
 * @param {Function} saveTgzThen
 * @param {Object} log
 * @param {Function} cprThen
 * @param {process} process
 * @returns {Function}
 */
exports.wiretree = function writeDependenciesModule (config, treeClimber, path, saveTgzThen, log, cprThen, process) {
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

      if (value.indexOf(config.FILE_TOKEN) === -1) {
        writePromise = saveTgzThen(dependencyName, value, {
          path: fullPath,
          strip: 1
        });
      } else {
        var partialPath = value.replace(config.FILE_TOKEN, '');
        var resolvedPath = path.resolve(process.cwd(), partialPath);

        writePromise = cprThen(resolvedPath, fullPath);
      }

      return writePromise.then(function logSave () {
        log.write('Wrote', log.green(dependencyName), 'to', fullPath);
      });
    }, TREE_SEP);
  };
};
