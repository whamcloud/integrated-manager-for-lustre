/* jshint node:true */
'use strict';

/**
 * Turns an stack trace into an ordered collection of objects.
 * Each object represents one line in the trace.
 *
 * @param {String} traceFile The actual error string.
 * @returns {Array}
 */
module.exports = function buildTraceCollection (traceFile) {

  var traceItemRegex = /(http.+):(\d+):(\d+)/;

  var filterOutRegex = regexFilter(traceItemRegex);

  var buildMatchWithRegex = runWith(traceItemRegex, buildMatchObject);

  return splitIt(traceFile, /\n/)
    .filter(filterOutRegex)
    .map(buildMatchWithRegex);

};

/**
 * Pulls the relevant bits of a String into an object literal.
 * @param {RegExp} traceLineRegex
 * @param {String} traceLine
 * @returns {{compiledLine: string, url: string, line: number, column: number}}
 */
function buildMatchObject (traceLineRegex, traceLine) {
  var matchObject = {compiledLine: '', url: '', line: 0, column: 0};

  var traceLineArr = traceLine.match(traceLineRegex);

  if (traceLineArr) {
    matchObject.compiledLine = traceLineArr.input;
    matchObject.url = traceLineArr[1];
    matchObject.line = parseInt(traceLineArr[2]);
    matchObject.column = parseInt(traceLineArr[3]);
  }

  return matchObject;
}

/**
 * HOF. Returns a function applied to the "closure'd" params and the inner functions param.
 * @param {RegExp} expression
 * @param {Function} func
 * @returns {Function}
 */
function runWith (expression, func) {
  return function innerRunWith (line) {
    return func(expression, line);
  };
}

/**
 * HOF. Returns null if a match is not found, and an array object if a match is found.
 * @example 'regex' is not matched within 'it'.
 * // returns null
 * regex === /(http.+):(\d+):(\d+)/
 * it === 'Error: hi'
 *
 * @example 'regex' is matched within 'it'.
 * // returns ["https://localhost:8000/static/chroma_ui/built-720c7e70.js:25:27625",
 * "https://localhost:8000/static/chroma_ui/built-720c7e70.js", "25", "27625"]
 * regex === /(http.+):(\d+):(\d+)/
 * it === 'at Object.t.filter.onFilterView (https://localhost:8000/static/chroma_ui/built-720c7e70.js:25:27625)'
 * @param {RegExp} regex
 * @returns {Function}
 */
function regexFilter (regex) {
  return function innerRegexFilter (it) {
    return it.match(regex);
  };
}

/**
 * Splits a string by a regex char.
 * @param {String} it
 * @param {RegExp} splitRegex
 * @returns {Array}
 */
function splitIt (it, splitRegex) {
  return it.split(splitRegex);
}
