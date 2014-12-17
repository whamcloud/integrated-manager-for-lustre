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


(function () {
  'use strict';

  var _ = (function getLoDash() {
    if (typeof window !== 'undefined')
      return window._;
    else
      return require('lodash');
  }());

  var mixins = {
    /**
     * HOF. Unary function.
     * @param {Function} fn
     * @returns {Function}
     */
    unary: function unaryWrap (fn) {
      return function unary (arg) {
        return fn(arg);
      };
    },
    /**
     * HOF. Binary function.
     * @param {Function} fn
     * @returns {Function}
     */
    binary: function binaryWrap (fn) {
      return function binary (arg1, arg2) {
        return fn(arg1, arg2);
      };
    },
    /**
     * Curried. Given a traditional tasty pie bulk response
     * unwraps it and transforms the objects.
     * @param {Function} fn
     * @param {Object} response
     * @returns {Object} Returns the response back.
     */
    unwrapResponse: _.curry(function (fn, response) {
      response.body.objects = fn(response.body.objects);

      return response;
    }),
    /**
     * Curried. Given a predicate, only executes the function
     * with val if the predicate passes.
     * @param {Function} pred
     * @param {Function} func
     * @param {*} val
     * @returns {*} The result of func on val.
     */
    if: _.curry(function ifTest (pred, func, val) {
      if (pred(val))
        return func(val);
    }),
    /**
     * Existence check.
     * @param {*} item
     * @returns {Boolean}
     */
    exists: function exists (item) {
      return item != null;
    },
    /**
     * Curried. A functional reduce.
     * @param {Function} func
     * @param {Array} coll
     * @returns {*}
     */
    freduce: _.curry(function reducer (func, coll) {
      return coll.reduce(_.binary(func));
    }),
    /**
     * Curried. A functional map.
     * @param {Function} func
     * @param {Array|Object} coll
     * @returns {Array|Object}
     */
    fmap: _.curry(function mapper (func, coll) {
      if (Array.isArray(coll))
        return coll.map(_.unary(func));
      else
        return Object.keys(coll).reduce(function (obj, key) {
          obj[key] = func(coll[key]);

          return obj;
        }, {});
    }),
    /**
     * Curried. A functional filter.
     * @param {Function} func
     * @param {Array} coll
     * @returns {Array}
     */
    ffilter: _.curry(function filterer (func, coll) {
      return coll.filter(_.unary(func));
    }),
    /**
     * A functional map that pulls a property
     * @param {String} property
     * @returns {Array|Object}
     */
    fmapProp: function fmapProp (property) {
      return _.fmap(_.property(property));
    },
    /**
     * A functional map that pulls properties
     * @param {Function|[String]} properties
     * @returns {Array|Object}
     */
    fmapProps: function fmapProp (properties) {
      return _.fmap(_.properties(properties));
    },
    /**
     * HOF. A functional identity
     * @param {*} item
     * @returns {Function}
     */
    fidentity: function fidentity (item) {
      return function identity () {
        return item;
      };
    },
    /**
     * Curried. Pulls items from an object.
     * @param {Function|String[]} sel
     * @param {Object} obj
     * @returns {Object}
     */
    properties: _.curry(function properties (sel, obj) {
      return _.pick(obj, sel);
    }),
    /**
     * Inverts the item.
     * @param {*} item
     * @returns {Boolean}
     */
    inverse: function inverse (item) {
      return !item;
    },
    /**
     * Curried. Returns the index of the first matching
     * search occurrence.
     * @param {String} sep
     * @param {String} path
     * @param {*} search
     */
    pathPointer: _.curry(function inPath (sep, path, search) {
      var foundAt = -1;

      path.split(sep).some(function findMatch (item, index) {
        var match = (item === search);

        if (match)
          foundAt = index;

        return match;
      });

      return foundAt;
    }),
    /**
     * Curried. Gets the subpath of the first matching
     * search occurrence.
     * @param {String} sep
     * @param {String} path
     * @param {*} search
     */
    subPath: _.curry(function subPath (sep, path, search) {
      var pointer = _.pathPointer(sep, path, search);

      if (pointer === -1)
        return;

      return path.split(sep).slice(0, pointer + 1).join(sep);
    }),
    /**
     * Curried. Plucks the path from the given item.
     * Splits on the given sep.
     * @param {String} sep
     * @param {String} path
     * @param {Array|Object} item
     * @returns {*} The item at the end of the path.
     */
    pluckPathSep: _.curry(function pluckPathSep (sep, path, item) {
      return path.split(sep)
        .reduce(function iteratePath (pointer, part) {
          return pointer[part];
        }, item);
    }),
    /**
     * Curried. Plucks the path from the given item.
     * @param {String} path
     * @param {Array|Object} item
     * @returns {*} The item at the end of the path.
     */
    pluckPath: _.curry(function pluckPath (path, item) {
      return _.pluckPathSep('.', path, item);
    }),
    /**
     * Given a collection and some properties,
     * tries to find a matching record for each item
     * passing through
     * @param {Function|String[]} sel
     * @param {Array|Object|String} coll
     * @param {Object} obj
     * @returns {Object|undefined}
     */
    findInCollection: _.curry(function findInCollection (sel, coll, obj) {
      var props = _.pick(obj, sel);

      return _.find(coll, props);
    }),
    /**
     * Truncates the destination array and pushes the source into it.
     * Operates in place.
     * @param {Array} destination
     * @param {Array} source
     * @throws {Error} Both arguments must be of type Array.
     * @returns {Array} The destination.
     */
    replace: function replace (destination, source) {
      if (!Array.isArray(destination) || !Array.isArray(source))
        throw new Error('Both arguments to replace must be arrays.');
      destination.length = 0;
      source.forEach(function populateDestination (item) {
        destination.push(item);
      });
      return destination;
    },
    /**
     * Takes an object and deletes the keys it holds.
     * @param {Object} obj
     * @returns {Object} Returns the passed in obj.
     */
    clear: function clear (obj) {
      var keys;
      try {
        keys = Object.keys(obj);
      } catch (error) {
        throw new Error('Object to clear must be an object!');
      }
      keys.forEach(function removeProperties (key) {
        delete obj[key];
      });
      return obj;
    },
    /**
     * Capitalizes a string.
     * @param {String} str
     * @returns {String}
     */
    capitalize: function capitalize (str) {
      return str[0].toUpperCase() + str.slice(1);
    },
    /**
     * Given a count and a string map, looks up the pluralization value
     * from the map. If key doesn't exist, falls back to stringMap.other.
     * If stringMap.other doesn't exist, falls back to empty string.
     * @param {Number|String} count
     * @param {Object} stringMap
     * @returns {String}
     */
    pluralize: function pluralize (count, stringMap) {
      var msg = stringMap[count] || stringMap.other || '';
      return msg.replace('{}', count.toString());
    },
    /**
     * Given an API like value, converts it to a capitalized
     * string of words.
     * @param {String} str
     * @returns {String}
     */
    apiToHuman: function apiToHuman (str) {
      return _.capitalize(str.split('_').join(' '));
    }
  };

  _.mixin(mixins);

  if (typeof module !== 'undefined')
    module.exports = _;
}());
