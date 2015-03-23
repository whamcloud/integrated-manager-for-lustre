'use strict';
/**
 * Creates a config object used throughout the app.
 * @param {process} process
 * @param {path} path
 * @param {Function} configulator
 * @returns {Object}
 */
exports.wiretree = function configModule (process, path, configulator) {
  var config = configulator({
    default: {
      FILE_TOKEN: 'file://',
      tarGzRegexp: /\.tar\.gz$/,
      registryUrl: 'https://registry.npmjs.org/',
      proxyUrl: process.env.HTTP_PROXY,
      ziplockDir: process.env.ZIPLOCK_DIR,
      packageName: path.basename(process.cwd()),
      ziplockPath: path.join(process.cwd(), 'ziplock.json'),
      DEP_TYPES: Object.freeze({
        DEPS: 'dependencies',
        OPTIONAL: 'optionalDependencies',
        DEV: 'devDependencies'
      }),
      askQuestions: true
    },
    development: {},
    production: {}
  });

  Object.defineProperty(config, 'depPath', {
    /**
     * Gets the dependency path, which is the combination of the ziplockDir and packageName.
     * @throws {Error}
     * @returns {String}
     */
    get: function getDepPath () {
      if (!this.ziplockDir)
        throw new Error('ziplockDir is not defined, export a ZIPLOCK_DIR environment variable or \
set --overrides.ziplockDir.');

      var resolvedPath = path.resolve(this.ziplockDir);
      return path.join(resolvedPath, this.packageName);
    }
  });

  return config;
};
