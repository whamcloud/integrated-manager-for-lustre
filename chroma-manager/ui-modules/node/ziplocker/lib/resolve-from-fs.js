'use strict';

/**
 * Resolves module info from a FS based package
 * @param {Object} fsThen
 * @param {path} path
 * @param {process} process
 * @param {Object} config
 * @returns {Function}
 */
exports.wiretree = function resolveFromFsModule (fsThen, path, process, config) {
  return function resolveFromFs (filePath) {
    var partialPath = filePath.replace(config.FILE_TOKEN, '');
    return fsThen.readFile(path.resolve(process.cwd(), partialPath, 'package.json'), 'utf8')
      .then(JSON.parse)
      .then(function buildResponseObject (packageJson) {
        return {
          response: packageJson,
          value: filePath
        };
      });
  };
};
