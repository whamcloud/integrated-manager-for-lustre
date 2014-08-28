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


angular.module('socket-module')
  .constant('VERBS', Object.freeze({
    GET: 'get',
    PUT: 'put',
    POST: 'post',
    DELETE: 'delete',
    PATCH: 'patch'
  }))
  .factory('requestSocket', ['$q', 'socket', 'VERBS', function requestSocketFactory ($q, socket, VERBS) {
    'use strict';

    /**
     * An abstraction for obtaining a spark from the request channel.
     * returns {Object}
     */
    return function requestSocket () {
      var spark = socket('request');

      Object.keys(VERBS).forEach(function setupVerbs (key) {

        /**
         * Wraps sending for each verb.
         * Removes leading api out of path.
         * Allows ack to be handled by a promise if true is passed for ack param.
         * @param {String} path
         * @param {Object} [options]
         * @param {Function|Boolean} [ack] If Function, behaves as normal. If boolean true, handles ack in promise.
         * @returns {Object} The spark or a promise.
         */
        spark['send' + _.capitalize(VERBS[key])] = function sendVerb (path, options, ack) {
          options = _.merge({}, options, {
            method: VERBS[key]
          });

          var data = {
            path: path.replace(/^\/?api/, ''),
            options: options
          };

          if (ack === true) {
            var deferred = $q.defer();

            ack = function deferredAck (response) {
              if ('error' in response)
                deferred.reject(response);
              else
                deferred.resolve(response);
            };

            spark.send('req', data, ack);

            return deferred.promise;
          }

          return spark.send('req', data, ack);
        };
      });

      return spark;
    };
  }])
  .factory('arrayOrItem', [function arrayOrItemFactory () {
    'use strict';

    /**
     * Calls fn for each item in a collection or once
     * for an individual response.
     * @param {Function} fn
     * @param {Object} response
     */
    return function arrayOrItem (fn, response) {
      if (Array.isArray(response.body.objects))
        response.body.objects = response.body.objects.map(fn);
      else
        response.body = fn(response.body);

      return response;
    };
  }])
  .factory('throwIfError', [function throwIfErrorFactory () {
    'use strict';

    /**
     * HOF. Throws if error, calls fn if not.
     * @param {Function} fn
     * @returns {Function}
     */
    return function throwIfError (fn) {
      return function checkforError (response) {
        if ('error' in response)
          throw response.error;

        return fn(response);
      };
    };
  }]);
