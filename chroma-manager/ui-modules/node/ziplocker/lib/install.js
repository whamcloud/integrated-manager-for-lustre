'use strict';

/**
 * Installs dependencies.
 * @param {Function} cprThen
 * @param {Object} config
 * @param {path} path
 * @param {Function} execThen
 * @param {Object} treeClimber
 * @param {Function} ziplockJson
 * @param {Promise} Promise
 * @param {Function} delThen
 * @param {Object} log
 * @param {Object} process
 * @returns {{prod: Function, dev: Function}}
 */
exports.wiretree = function installModule (cprThen, config, path, execThen, treeClimber,
                                           ziplockJson, Promise, delThen, log, process) {

  var NODE_MODULES = 'node_modules';

  var replaceRegexp = new RegExp(config.DEP_TYPES.DEPS + '|' + config.DEP_TYPES.DEV, 'g');
  var optionalDepsRegexp = new RegExp(config.DEP_TYPES.OPTIONAL + '/[^/]+/version$');

  var modulesDir = path.join(process.cwd(), NODE_MODULES);
  var zipDir = path.join(config.depPath, NODE_MODULES);
  var zipDirDev = path.join(config.depPath, config.DEP_TYPES.DEV);

  return {
    prod: createInstall(identity, filterFiles),
    dev: createInstall(buildFunc(cprThen, zipDirDev, modulesDir), identity)
  };

  /**
   * HOF that installs deps.
   * Can be configured for installing devDependencies.
   * @param {Function} moveDevFiles
   * @param {Function} filterFiles
   * @returns {Function}
   */
  function createInstall (moveDevFiles, filterFiles) {
    return function install () {
      return delThen(modulesDir)
        .then(buildFunc(cprThen, zipDir, modulesDir))
        .then(moveDevFiles)
        .then(buildFunc(execThen, 'npm rebuild')).then(logExec)
        .then(gatherOptionalDeps)
        .then(filterFiles)
        .then(buildOptionalDeps)
        .then(buildFunc(log.write, log.green('installed depedencies'), 'to', process.cwd()));
    };
  }

  /**
   * Reads the ziplock.json file and
   * returns any optional deps found.
   * @returns {Promise}
   */
  function gatherOptionalDeps () {
    return ziplockJson.readFile()
      .then(JSON.parse)
      .then(function getOptionalDeps (json) {
        var optionalDeps = [];

        treeClimber.climb(json, function visitor (key, value, fullPath) {
          if (fullPath.match(optionalDepsRegexp))
            optionalDeps.push(path.dirname(fullPath));
        }, '/');

        return optionalDeps;
      });
  }

  /**
   * Builds any optional dependencies
   * Continues on if optional dep fails
   * @param {Array} optionalDeps
   * @returns {Promise}
   */
  function buildOptionalDeps (optionalDeps) {
    return optionalDeps.reduce(function buildPromiseChain (promise, optionalDep) {
      return promise.then(function tryBuild () {
        var fullPath = path.join(process.cwd(), optionalDep.replace(replaceRegexp, NODE_MODULES));

        return execThen('npm build ' + fullPath).then(logExec)
          .then(buildFunc(log.write, 'built', log.yellow('optional dependency'), 'at', fullPath))
          .then(buildFunc(cprThen, fullPath, fullPath.replace(config.DEP_TYPES.OPTIONAL, NODE_MODULES)))
          .catch(function recover (err) {
            log.write('did not build', log.yellow('optional dependency'), 'at', fullPath);
            log.write(err.message);
          })
          .then(buildFunc(delThen, fullPath));
      });
    }, Promise.resolve());
  }

  /**
   * Given an array for file paths, removes the ones
   * used in development.
   * @param {Array} optionalDeps
   * @returns {Array}
   */
  function filterFiles (optionalDeps) {
    return optionalDeps.filter(function removeDev (optionalDep) {
      return !optionalDep.match(config.DEP_TYPES.DEV);
    });
  }

  /**
   * A simple identity function
   * @param {*} x
   * @returns {*}
   */
  function identity (x) { return x; }

  /**
   * HOF that is sort of like partial, except
   * additional arguments are not added to the return call.
   * @param {Function} func
   * @returns {Function}
   */
  function buildFunc (func) {
    var args = Array.prototype.slice.call(arguments, 1);

    return function builtFunc () {
      return func.apply(null, args);
    };
  }

  /**
   * Logs the output
   * @param {Array} outputs
   */
  function logExec (outputs) {
    outputs
      .filter(function removeEmpty (output) {
        return output.length;
      })
      .forEach(unary(log.write));
  }

  /**
   * HOF that only passes the first argument through.
   * @param {Function} func
   * @returns {Function}
   */
  function unary (func) {
    return function unaryCall (arg) {
      return func(arg);
    };
  }
};
