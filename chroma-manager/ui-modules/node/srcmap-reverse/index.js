/* jshint node:true */
'use strict';

var sm = require('source-map');
var SourceMapConsumer = sm.SourceMapConsumer;
var smc;
var buildTraceCollection = require('./build-trace-collection');

module.exports = {
  reverseSourceMap: reverseSourceMap,
  buildTraceCollection: buildTraceCollection,
  flattenTraceCollection: flattenTraceCollection
};

/**
 * Reverse a source map.
 * @param {Object} trace At minimum, an line and column number in an object.
 * @param {Object|String} sourceMap Json obj or string.
 * @returns {Object}
 */
function reverseSourceMap (trace, sourceMap) {

  var reversedTrace;

  smc = new SourceMapConsumer(sourceMap);

  reversedTrace = smc.originalPositionFor(trace);

  return reversedTrace;

}

/**
 * Turns a trace collection into a string for output.
 * @param {Array} reversedCollection
 * @returns {String}
 */
function flattenTraceCollection (reversedCollection) {

  return prepareForDisplay(buildTraceLine(reversedCollection));

}

/**
 * Takes a collection and turns into one line, nearly ready for the ui.
 * @param {Array} coll
 * @returns {String}
 */
function buildTraceLine (coll) {
  return coll
    .reduce(function reducer (inital, obj) {

      // Fixup the symbol name
      var name = obj.name || '';
      if (name) name = name + ' ';

      return inital + name + obj.source + ':' + obj.line + ':' + obj.column + '\n';
    }, '');
}

/**
 * Add the proper text to the output string; for making it look good in the ui.
 * @param {String} trace
 * @returns {string}
 */
function prepareForDisplay (trace) {
  var result = '';

  trace.split('\n')
    .forEach(function enumerator (line) {

      if (line !== '')
        result = result + 'at ' + line + '\n';

    });

  return result;
}
