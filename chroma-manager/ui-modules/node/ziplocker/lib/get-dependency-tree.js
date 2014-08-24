'use strict';

/**
 * Builds a dependency tree by making recursive calls to the registry.
 * @param {Object} packageJson
 * @param {Promise} Promise
 * @param {Object} log
 * @param {Object} semver
 * @param {Object} config
 * @param {Function} resolveFromFs
 * @param {Function} resolveFromRegistry
 * @param {Function} resolveFromGithub
 * @returns {Function}
 */
exports.wiretree = function getDependencyTreeModule (packageJson, Promise, log, semver,
                                                     config, resolveFromFs, resolveFromRegistry, resolveFromGithub) {
  /**
   * Responsible for building out the tree recursively using promises.
   * @returns {Promise}
   */
  return function getTree () {
    return buildTree(packageJson, {}, true);
  };

  /**
   * Recursively builds a dependency tree
   * @param {Object} packageJson package.json type data describing the dependencies.
   * @param {Object} tree The tree or branch of the tree being built.
   * @param {Boolean} useDevDependencies Should devDependencies be spidered?
   * @returns {Promise}
   */
  function buildTree (packageJson, tree, useDevDependencies) {
    var devDepsPromise = (useDevDependencies ?
      buildDependencies(config.DEP_TYPES.DEV, packageJson, tree) :
      Promise.resolve());

    var optionalDeps = packageJson[config.DEP_TYPES.OPTIONAL];
    var deps = packageJson[config.DEP_TYPES.DEPS];

    // Dedupe deps.
    if (optionalDeps && deps)
      Object.keys(optionalDeps).forEach(function removeDuplicateKeys (key) {
        if (deps[key] === optionalDeps[key])
          delete deps[key];
      });

    return Promise.all([
      buildDependencies(config.DEP_TYPES.DEPS, packageJson, tree),
      buildDependencies(config.DEP_TYPES.OPTIONAL, packageJson, tree),
      devDepsPromise
    ])
    .then(function returnTree () {
      return tree;
    });
  }

  /**
   * Fetches dependencies and writes info to the tree.
   * @param {DEP_TYPES} type
   * @param {Object} packageJson package.json type data describing the dependencies.
   * @param {Object} tree The tree or branch of the tree being built.
   * @returns {Promise}
   */
  function buildDependencies (type, packageJson, tree) {
    if (!packageJson[type])
      return Promise.resolve();

    var dependencyPromises = Object.keys(packageJson[type])
      .map(function getDependencies (dependency) {
        var dependencyValue = packageJson[type][dependency];

        var resolveModule;
        if (dependencyValue.indexOf(config.FILE_TOKEN) !== -1)
          resolveModule = resolveFromFs(dependencyValue);
        else if (semver.validRange(dependencyValue))
          resolveModule = resolveFromRegistry(dependency, dependencyValue);
        else
          resolveModule = resolveFromGithub(dependencyValue);

        return resolveModule.then(function buildTreeComponent (obj) {
          if (!tree[type])
            tree[type] = {};

          tree[type][dependency] = { version: obj.value };

          log.write('resolved', log.green(type), dependency, 'to', obj.value);

          return buildTree(obj.response, tree[type][dependency]);
        });
      });

    return Promise.all(dependencyPromises);
  }
};
