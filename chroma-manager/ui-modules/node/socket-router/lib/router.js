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


'use strict';

var format = require('util').format;
var find = require('lodash.find');
var pathRegexp = require('path-to-regexp');
var verbs = ['get', 'post', 'put', 'patch', 'delete'];
var verbsPlusAll = verbs.concat('all');
var routes = [];

/**
 * A router singleton.
 * @type {{route: Function, go: Function, reset: Function, verbs: Object}}
 */
var router = {
  /**
   * Adds a path to the list of routes.
   * @param {String} path The path to match.
   * @returns {Object} A pathRouter object.
   */
  route: function addRoute (path) {
    var route = find(routes, { path: path });

    if (route)
      return route.pathRouter;

    var keys = [];
    var pathRouter = getAPathRouter();

    route = {
      path: path,
      keys: keys,
      regexp: pathRegexp(path, keys),
      pathRouter: pathRouter
    };

    routes.push(route);

    return pathRouter;
  },
  /**
   * Goes to the provided path. If not found throws an error.
   * Takes variable arguments, the first of which is a required path.
   * @param {String|RegExp} path
   * @param {String} verb
   * @param {Object} spark
   * @param {Object} [data]
   * @param {Function} [ack]
   * @throws {Error}
   */
  go: function go (path, verb, spark, data, ack) {
    var matched = routes.some(function findMatch (route) {
      var action;

      var matches = route.regexp.exec(path);

      if (!matches) return false;

      if (route.pathRouter.verbs[verb] != null)
        action = route.pathRouter.verbs[verb];
      else if (route.pathRouter.verbs.all != null)
        action = route.pathRouter.verbs.all;
      else
        throw new Error(format('Route: %s does not have verb %s', path, verb));

      var req = {
        params: keysToParams(route.keys, matches),
        matches: matches,
        verb: verb,
        data: data
      };

      var resp = {
        spark: spark,
        ack: ack
      };

      action(req, resp);

      return true;
    });

    if (!matched)
      throw new Error(format('Route: %s does not match provided routes.', path));

    function keysToParams (keys, matches) {
      return keys.reduce(function convertToParams (params, key, index) {
        params[key.name] = matches[index + 1];

        return params;
      }, {});
    }
  },
  /**
   * Resets the routes list to an empty state
   */
  reset: function reset () {
    routes.length = 0;
  },
  verbs: verbs.reduce(function buildVerbObject (verbs, verb) {
    verbs[verb.toUpperCase()] = verb;

    return verbs;
  }, {})
};

verbsPlusAll.forEach(function addVerbToRouter (verb) {
  router[verb] = function addVerbToRouterInner (path, action) {
    router.route(path)[verb](action);

    return this;
  };
});

module.exports = router;

/**
 * Creates an object that holds route actions corresponding to a given verb.
 * @returns {Object}
 */
function getAPathRouter () {
  return verbsPlusAll.reduce(function buildMethods (pathRouter, verb) {
    /**
     * Pushes a verb corresponding to an action into this router's
     * verb list.
     * @param {Function} action
     * @returns {Object}
     */
    pathRouter[verb] = function verbMapper (action) {
      pathRouter.verbs[verb] = action;

      return pathRouter;
    };

    return pathRouter;
  }, { verbs: {} });
}
