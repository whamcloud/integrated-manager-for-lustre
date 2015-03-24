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
  return function resolveFromFs (filePath, currentPath) {
    var partialPath = filePath.replace(config.FILE_TOKEN, '');
    var newPath = path.resolve(currentPath, partialPath);
    var newFilePath = config.FILE_TOKEN + path.relative(process.cwd(), newPath);

    return fsThen.readFile(path.join(newPath, 'package.json'), 'utf8')
      .then(JSON.parse)
      .then(function buildResponseObject (packageJson) {
        return {
          response: packageJson,
          value: newFilePath,
          newPath: newPath
        };
      });
  };
};
