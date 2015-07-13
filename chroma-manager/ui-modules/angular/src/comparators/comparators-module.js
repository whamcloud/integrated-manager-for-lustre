//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


(function () {
  'use strict';

  var comparators = {
    /**
     * HOF that receives a list of predicate arguments and verifies each predicate. This
     * is a variadic function.
     * @returns {Function}
     */
    and: function and () {
      var functions = [].slice.call(arguments, 0);
      return function innerAnd () {
        return functions.every(function checkPredicate (predicate) {
          return predicate();
        });
      };
    },

    /**
     * Receives a predicate or a comparator, which computes multiple predicates. Depending on the value returned,
     * the truthy or falsy function will be invoked with the list of arguments passed into the function.
     * @param {Function} predicate
     * @param {Function} truthy
     * @param {Function} [falsy]
     * @returns {Function}
     */
    maybe: function maybe (predicate, truthy, falsy) {
      return function innerMaybe () {
        if (predicate.apply(this, arguments))
          return truthy.apply(this, arguments);
        else if (falsy)
          return falsy.apply(this, arguments);
      };
    },

    /**
     * HOF that returns a function that returns the specified value
     * @param {*} val
     * @returns {Function}
     */
    memorizeVal: function memorizeVal (val) {
      return function innerReturnVal () {
        return val;
      };
    },

    /**
     * HOF that returns a function that will return the inverse value of the function that is passed
     * @param {Function} func
     * @returns {Function}
     */
    not: function not (func) {
      return function innerNot () {
        return !func.apply(this, arguments);
      };
    },

    /**
     * HOF that indicates if a value being passed is true
     * @param {*} val
     * @returns {Function}
     */
    isTrue: function isTrue (val) {
      return function innerTrue () {
        return val === true;
      };
    },

    /**
     * HOF that indicates if a value being passed is false
     * @param {*} val
     * @returns {Function}
     */
    isFalse: function isFalse (val) {
      return comparators.not(comparators.isTrue(val));
    },

    /**
     * HOF that indicates if an item passed is null, undefined, or an empty string
     * @param {*} item
     * @returns {Function}
     */
    empty: function empty (item) {
      return function innerEmpty () {
        return item == null || item === '';
      };
    },

    /**
     * HOF that indicates if a is equal (strict) to b
     * @param {*} a
     * @param {*} b
     * @returns {Function}
     */
    referenceEqualTo: function referenceEqualTo (a, b) {
      return function innerReferenceEqualTo () {
        return a === b;
      };
    },

    /**
     * HOF that indicates if a is less than b
     * @param {*} a
     * @param {*} b
     * @returns {Function}
     */
    lessThan: function lessThan (a, b) {
      return function innerLessThan () {
        return a < b;
      };
    },

    /**
     * HOF that indicates if a is greater than b
     * @param {*} a
     * @param {*} b
     * @returns {Function}
     */
    greaterThan: function greaterThan (a, b) {
      return function innerGreaterThan () {
        return a > b;
      };
    }
  };

  // Pass the entire comparators object as a dependency
  angular.module('comparators', []).value('comparators', comparators);

  // Individualize each comparator so that only what is needed is injected
  Object.keys(comparators).forEach(function createComparatorService (name) {
    angular.module('comparators').factory(name, [function returnComparator () {
      return comparators[name];
    }]);
  });
}());
