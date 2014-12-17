'use strict';

/**
 * Writes a ziplock.json to the FS
 * @param {process} process
 * @param {Object} config
 * @param {Function} fsThen
 * @param {Function} getDependencyTree
 * @param {Object} log
 * @param {Object} _
 * @returns {Object}
 */
exports.wiretree = function ziplockJsonModule (process, config, fsThen, getDependencyTree, log, _) {
  return {
    writeFile: writeFile,
    readFile: readFile
  };

  /**
   * Responsible for writing a ziplock.json file.
   * @returns {Promise}
   */
  function writeFile () {
    return readFile()
      .then(JSON.parse)
      .then(function diffZiplockTrees (originalTree) {
        return getDependencyTree().then(function logTree (tree) {
          if (config.askQuestions && !_.isEqual(originalTree, tree)) {
            log.diffObjects(tree, originalTree);
            return log.question.yesOrNo('The local tree has changed. Do you wish to continue (y, n):  ')
              .then(function handleAnswer (wishToContinue) {
                if (!wishToContinue)
                  process.exit(0);

                return writeZiplockFile(tree);
              });
          }

          return tree;
        });
      })
      .catch(function handleError (error) {
        if (error.code === 'ENOENT')
          return getDependencyTree()
            .then(writeZiplockFile);
        else
          throw error;
      });
  }

  /**
   * Writes the ziplock.json file to the ziplockPath.
   * @param {Object} json
   * @returns {Promise}
   */
  function writeZiplockFile (json) {
    return fsThen
      .writeFile(config.ziplockPath, JSON.stringify(json, null, 2))
      .then(function returnZiplockJson () {
        log.write('Wrote', log.green('ziplock.json'), 'to', config.ziplockPath);

        return json;
      });
  }

  /**
   * Reads the ziplock file.
   * @returns {Promise}
   */
  function readFile () {
    return fsThen.readFile(config.ziplockPath, { encoding: 'utf8' });
  }
};
