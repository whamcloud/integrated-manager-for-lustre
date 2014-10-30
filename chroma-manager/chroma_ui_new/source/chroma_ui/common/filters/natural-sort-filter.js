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

angular.module('filters').filter('naturalSort', [function naturalSort () {
  'use strict';

  var re = /([a-zA-Z]+)|([0-9]+)/g;
  var getStringToSort;

  /**
   * Sorts in natural order as opposed to lexical order
   * @param {Array} input
   * @param {Function} predicate Used to retrieve the value in context
   * @param {Boolean} reverse Indicates if the sorted array should be reversed
   */
  return function orderArrayUsingNaturalSort (input, predicate, reverse) {
    getStringToSort = predicate;
    var sortedArray = input.sort(naturalSortAlgorithm);

    if (reverse === true) {
      sortedArray.reverse();
    }

    return sortedArray;
  };

  /**
   * Performs the natural sort algorithm
   * @param {String|Number} a
   * @param {String|Number} b
   * @returns {String|Number}
   */
  function naturalSortAlgorithm (a, b) {
    var componentsInA = splitStringIntoComponents(getStringToSort(a));
    var componentsInB = splitStringIntoComponents(getStringToSort(b));

    var result = 0;
    var pos = 0;

    do {
      result = calculateResult(pos, componentsInA, componentsInB);
      pos += 1;
    } while (result === 0);

    return result;
  }

  /**
   * Calculates the result based on the component values.
   * @param {Number} pos
   * @param {Array} componentsInA
   * @param {Array} componentsInB
   * @returns {Number}
   */
  function calculateResult (pos, componentsInA, componentsInB) {
    var result = 0;

    if (pos >= componentsInA.length) {
      result = -1;
    } else if (pos >= componentsInB.length) {
      result = 1;
    } else if (typeof componentsInA[pos] === 'number' && typeof componentsInB[pos] === 'string') {
      result = -1;
    } else if (typeof componentsInA[pos] === 'string' && typeof componentsInB[pos] === 'number') {
      result = 1;
    } else {
      result = calculateValueForALessThanB(componentsInA[pos], componentsInB[pos]);
      result = calculateValueForAEqualB(componentsInA[pos], componentsInB[pos], result);
    }

    return result;
  }

  /**
   * returns -1 if a < b. Returns 1 otherwise.
   * @param {Number|String} a
   * @param {Number|String} b
   * @returns {Number}
   */
  function calculateValueForALessThanB (a, b) {
    return (a < b) ? -1 : 1;
  }

  /**
   * Returns 0 if a and b are equal. Returns the passed in result otherwise.
   * @param {Number|String} a
   * @param {Number|String} b
   * @param {Number} result
   * @returns {Number}
   */
  function calculateValueForAEqualB (a, b, result) {
    return (a === b) ? 0 : result;
  }

  /**
   * Splits the passed in string into components in a way such that strings and numbers
   * are separated.
   * @example
   * 'alpha123beta7gamma' => ['alpha', 123, 'beta', 7, 'gamma']
   * @param {String|Number}val
   * @returns {Array}
   */
  function splitStringIntoComponents (val) {
    if (typeof val === 'number')
      return [val];

    var m;
    var components = [];
    while ((m = re.exec(val)) != null) {
      if (m.index === re.lastIndex)
        re.lastIndex += 1;

      components.push(isNaN(m[0]) ? m[0] : +m[0]);
    }

    return components;
  }

}]);
