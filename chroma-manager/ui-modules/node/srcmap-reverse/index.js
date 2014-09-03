//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


/* jshint node:true */
'use strict';

var sm = require('source-map');
var SourceMapConsumer = sm.SourceMapConsumer;
var smc;
var buildTraceCollection = require('./build-trace-collection');

module.exports = {
  reverseSourceMap: reverseSourceMap,
  buildTraceCollection: buildTraceCollection,
  flattenTraceCollection: flattenTraceCollection,
  stripLongPaths: stripLongPaths,
  execute: execute
};

function execute (trace, sourceMap) {
  return stripLongPaths(
    flattenTraceCollection(
      buildTraceCollection(trace)
        .map(function reverseLine (traceLine) {
          return reverseSourceMap(traceLine, sourceMap);
        })
    )
  );
}

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

/**
 * Loops over a collection and calls the stripLong function, then rejoins with a newline char.
 * @param {String} trace
 * @returns {String}
 */
function stripLongPaths (trace) {
  return trace.split('\n').map(stripLong).join('\n');

  /**
   * Returns a new line w/o the long path.
   * @param {String} line
   * @returns {String}
   */
  function stripLong (line) {
    var splitVal = 'chroma_ui_new/';
    var newline;
    var arr;

    arr = line.split(splitVal);

    if(arr[1])
      newline = arr[0].split('/')[0] + arr[1];

    return newline;
  }
}
