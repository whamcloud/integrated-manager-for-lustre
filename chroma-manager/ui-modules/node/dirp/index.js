'use strict';

var _ = require('lodash-mixins');
var path = require('path');
var readDirSync = require('fs').readdirSync;
var statSync = require('fs').statSync;


/**
 * Loads all items in the specified directory and requires each file.
 * An object containing the data is returned.
 * @param {String} directory
 * @param {Function} [requireFile]
 * @returns {Object}
 */
module.exports = function loadDirectoryItems (directory, requireFile) {

  var files = readDirSync(directory);
  var filesToExclude = ['index.js', 'package.json', 'ziplock.json'];

  return _(files)
    .filter(filterOnlyFiles)
    .filter(filterFileName)
    .map(removeExtensionFromName)
    .mapKeys(_.camelCase)
    .mapValues(_.unary(path.join.bind(path, directory)))
    .mapValues(requireFile || require)
    .value();

  function filterOnlyFiles (name) {
    return statSync(path.join(directory,name)).isFile();
  }

  function removeExtensionFromName (filename) {
    var parts = filename.split('.');
    if (parts.length > 1)
      parts.pop();
    return parts.join('.');
  }

  function filterFileName (name) {
    return name[0] !== '.' && filesToExclude.indexOf(name) === -1;
  }
};
