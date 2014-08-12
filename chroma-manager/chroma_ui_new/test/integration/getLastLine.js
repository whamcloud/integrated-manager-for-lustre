#!/usr/bin/env node

/* jshint node:true */
/*global Promise:true */
/*global _:true */
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
function getLastLine (builtFilePath) {

  return globThen(builtFilePath)
    .then(isGlobResultValid)
    .then(getGlobbedFilePaths)
    .then(_.partialRight(readFileThen, 'utf8'))
    .then(getLast);

}

/**
 * Get the last file in the collection.
 * @param {Array} globbedFilePaths Collection of files that match the glob pattern.
 * @returns {String} The path to the minified file, after globbing for it.
 */
function getGlobbedFilePaths (globbedFilePaths) {
  return globbedFilePaths.pop();
}

/**
 * Check if the glob found a match.
 * If so, return the array.
 * If not, throw an error.
 * @param {Array} result Result of the glob search.
 * @returns {Array}
 */
function isGlobResultValid (result) {

  if (isValid(result))
    return result;
  else
    throw new Error('Glob failed to find a match.');

}

/**
 * Checks if the globResult is valid.
 * If the result's length is not greater than zero, the glob has failed to find
 * what it was looking for.
 * @param {Array} globResult
 * @returns {boolean}
 */
function isValid (globResult) {
  return globResult.length > 0;
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
