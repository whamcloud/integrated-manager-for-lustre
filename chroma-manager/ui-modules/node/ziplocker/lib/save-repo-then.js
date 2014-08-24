'use strict';

exports.wiretree = function saveRepoThenModule (parseGithubUrl, execThen, delThen, util) {
  /**
   * Saves a GitHub repo at the url to the specified path.
   * @param {String} url
   * @param {String} fullPath
   * @returns {Promise}
   */
  return function saveRepoThen (url, fullPath) {
    return parseGithubUrl(url)
      .then(function (parsed) {
        var cloneCommand = util.format('git clone git@github.com:%s %s', parsed.path, fullPath);

        return execThen(cloneCommand)
          .then(function () {
            return parsed;
          });
      })
      .then(function (parsed) {
        var resetToCommitCommand = util.format('git -C "%s" reset --hard %s', fullPath, parsed.commitIsh);
        return execThen(resetToCommitCommand);
      })
      .then(function () {
        var cleanCommand = util.format('git -C "%s" clean -f -d', fullPath);

        return execThen(cleanCommand);
      })
      .then(function () {
        return delThen(
          [
            fullPath + '/**/.git',
            fullPath + '/**/.gitignore',
            fullPath + '/**/.npmignore'
          ],
          { force: true }
        );
      });
  };
};
