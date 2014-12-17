'use strict';

var Wiretree = require('wiretree');
var path = require('path');

module.exports = createWiretree();

/**
 * Creates a wiretree.
 * @returns {Wiretree}
 */
function createWiretree () {
  var tree = new Wiretree(__dirname);
  tree.add(process, 'process');
  tree.add(console, 'console');
  tree.load(path.join(process.cwd(), 'package.json'), 'packageJson');

  var deps = {
    path: 'path',
    'fs-extra': 'fs',
    'child_process': 'childProcess',
    del: 'del',
    readline: 'readline',
    zlib: 'zlib',
    tar: 'tar',
    util: 'util',
    'tree-climber': 'treeClimber',
    promise: 'Promise',
    'request-then': 'requestThen',
    'request-then/node_modules/request': 'request',
    semver: 'semver',
    chalk: 'chalk',
    'unfunk-diff': 'unfunkDiff',
    'lodash-mixins': '_',
    configulator: 'configulator'
  };

  Object.keys(deps).forEach(function addDep (dep) {
    tree.add(require(dep), deps[dep]);
  });

  tree.folder(__dirname + '/lib', {
    transform: function transform (text) {
      return text.split(/\-|\./).reduce(function convert (str, part) {
        return (str += part.charAt(0).toUpperCase() + part.slice(1));
      });
    }
  });

  tree.add({ wiretree: main }, 'main');

  return tree;
}

/**
 * The main ziplock process.
 * @param {Function} ziplockJson
 * @param {Function} writeDependencies
 * @param {Object} config
 * @param {Function} delThen
 */
function main (ziplockJson, writeDependencies, config, delThen) {
  delThen(config.depPath, { force: true })
    .then(ziplockJson.writeFile)
    .then(writeDependencies)
    .done();
}
