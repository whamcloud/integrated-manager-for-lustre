#!/usr/bin/env node

/* jshint node:true */
'use strict';

var Promise = require('promise');
// Wrapping the glob function in a promise.
var globThen = Promise.denodeify(require('glob'));
var _ = require('lodash');
var readFileThen = Promise.denodeify(require('fs').readFile);

/**
 * Gets the last line in our compiled file.
 * @param {String} builtFilePath Path to the compiled javascript file.
 * @returns {Promise} The result of running through the promise chain.
 */
function getLastLine(builtFilePath) {

  return globThen(builtFilePath)
    .then(getGlobbedFilePath)
    .then(_.partialRight(readFileThen, 'utf8'))
    .then(getLast);

}

/**
 * Get the last file in the collection.
 * @param {Array} globbedFiles Collection of files that match the glob pattern.
 * @returns {String} The path to the minified file, after globbing for it.
 */
function getGlobbedFilePath (globbedFiles) {
  return globbedFiles.pop();
}

/**
 * Trims the file, and gets the last item after splitting the file
 * on the new line character.
 * @param {String} file The minified file.
 * @returns {String} The string that points to the minified file with '.map'
 * appended to the end.
 */
function getLast (file) {
  return file.trim().split('\n').pop();
}

if (require.main === module)
  getLastLine(__dirname + '/../../static/chroma_ui/built-*.js')
    .done(_.partial(console.log, '### last line: \n\t%s'));

module.exports = getLastLine;
