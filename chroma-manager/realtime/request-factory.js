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

/**
 * Returns a wrapped default request.
 * @param {Object} conf
 * @param {Object} requestModule
 * @param {Object} logger
 * @param {Q} Q
 * @param {Function} jsonMask
 * @param {Object} VERBS
 * @param {Object} _
 * @returns {Object}
 */
exports.wiretree = function requestFactory (conf, requestModule, logger, Q, jsonMask, VERBS, _) {
  var pendCount = 0;
  var defaultRequest = requestModule.defaults({
    json: true,
    strictSSL: false,
    useQuerystring: true,
    timeout: 325000, // 5 minutes 25 seconds.
    pool: {
      maxSockets: 20
    }
  });

  return Object.keys(VERBS)
    .map(function getVerb (key) {
      return VERBS[key];
    })
    .reduce(function buildRequests (verbs, currentVerb) {
      verbs[currentVerb] = getRequest(currentVerb);

      return verbs;
    }, {});

  /**
   * HOF. Returns a promise wrapped request.
   * @param {String} verb The type of request
   * @returns {Function}
   */
  function getRequest (verb) {
    /**
     * Makes the request. Outputs logging of request info.
     * @param {String} path The route to request
     * @params {Object} [options] Options taken by request.
     */
    return function promisifyRequest (path, options) {
      var time = process.hrtime();

      options = _.clone(options || {});

      pendCount += 1;

      var mask;
      if (typeof options.jsonMask === 'string') {
        mask = options.jsonMask;
        delete options.jsonMask;
      }

      path = path
        .replace(/^\/*/, '')
        .replace(/\/*$/, '/');

      var log = logger.child({
        path: path,
        verb: verb
      });

      return Q.ninvoke(defaultRequest, verb, conf.apiUrl + path, options)
        .spread(function logTiming (resp, body) {
          var diff = process.hrtime(time);
          var elapsed = parseInt(diff[1] / 1000000, 10); // divide by a million to get nano to milli

          log.debug('%s: %s (%d.%d seconds)', resp.statusCode, resp.request.href, diff[0], elapsed);

          return [resp, body];
        })
        .spread(function checkForError (resp, body) {
          if (resp.statusCode < 400)
            return resp;

          var message;

          try {
            message = JSON.stringify(body);
          } catch (e) {
            message = body;
          }

          var error = new Error(message);
          error.statusCode = resp.statusCode;

          throw error;
        })
        .then(function handleResponseBody (resp) {
          if (!resp.body)
            return resp;

          if (mask)
            resp.body = jsonMask(resp.body, mask);

          log.trace(resp.body);

          return resp;
        })
        .catch(function enhanceError (error) {
          error.message = error.message + ' During ' + verb + ' request to ' + path;

          log.error(error);

          throw error;
        })
        .finally(function allDone() {
          pendCount -= 1;

          log.trace('pend count is: %d', pendCount);
        });
    };
  }
};
