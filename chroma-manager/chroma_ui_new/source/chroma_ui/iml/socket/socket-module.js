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

  var socketModule = angular.module('socket-module', ['primus'])
    .factory('socket', ['$applyFunc', '$document', '$window', 'primus', 'runPipeline', socketFactory]);

  /**
   * Generates a new socket.
   * @param {Function} $applyFunc
   * @param {Object} $document
   * @param {Object} $window
   * @param {Function} primus
   * @param {Function} runPipeline
   * @returns {Object}
   */
  function socketFactory ($applyFunc, $document, $window, primus, runPipeline) {
    var EVENTS = Object.freeze({
      PIPELINE: 'pipeline',
      DATA: 'data'
    });

    /**
     * Connects to a socket and returns a spark from it.
     * @param {String} name The name of the channel to connect to.
     * @returns {Object}
     */
    return function socket (name) {
      var spark = primus().channel(name);
      var extendedSpark = Object.create(spark);

      /**
       * Decorates spark.on, making sure we are in Angular scope when invoking our handler.
       * @param {String} event
       * @param {Function} fn
       * @param {Object} context
       * @returns {Function}
       */
      extendedSpark.on = extendedSpark.addListener = function on (event, fn, context) {
        var newContext = Object.create(context || {});
        var $apply = $applyFunc(function handler () {
          if (event === EVENTS.DATA)
            extendedSpark.lastArgs = cloneDeepArguments(arguments);

          fn.apply(newContext, arguments);
        });

        newContext.off = function off () {
          spark.removeListener(event, $apply);
        };

        spark.on(event, $apply, newContext);

        return newContext.off;
      };

      /**
       * Provides a hook to set the last data stored
       * for onValue.
       */
      extendedSpark.setLastData = function setLastData () {
        extendedSpark.lastArgs = arguments;
      };

      /**
       * This acts like a Bacon property. It looks for last arg and if available, calls fn directly.
       * @param {String} event
       * @param {Function} fn
       * @param {Object} [context]
       * @returns {Function}
       */
      extendedSpark.onValue = function onValue (event, fn, context) {
        var off = extendedSpark.on(event, fn, context);

        var newContext = Object.create(context || {});
        newContext.off = off;

        if (extendedSpark.lastArgs) {
          var lastArgs = cloneDeepArguments(extendedSpark.lastArgs);

          if (event === EVENTS.PIPELINE) {
            var runNow = pipeline.slice(0, -1).concat(function callFunc (response) {
              fn.call(newContext, response);
            });

            runPipeline(runNow, lastArgs[0]);
          } else if (event === EVENTS.DATA) {
            fn.apply(newContext, lastArgs);
          }
        }

        return off;
      };

      var pipeline = [function emitPipeline (response) {
        spark.emit(EVENTS.PIPELINE, response);
      }];

      /**
       * Adds a new pipe into the pipeline
       * @param {Function} pipe
       * @returns {Object}
       */
      extendedSpark.addPipe = function addPipe (pipe) {
        pipeline.splice(-1, 0, pipe);

        if (pipeline.length === 2)
          extendedSpark.on(EVENTS.DATA, function run (response) {
            if (isEmitterTransport(response))
              return;

            runPipeline(pipeline, response);
          });

        return this;
      };

      var lastSend;

      /**
       * Sends data over the spark.
       * Adds in cookie to data for auth purposes.
       * @param {String} ev
       * @param {Object} data
       * @param {Function} [fn]
       * @returns {Object}
       */
      extendedSpark.send = function send (ev, data, fn) {
        var cookie = $document[0].cookie;
        data = _.merge({}, data, {
          options: {
            headers: {
              Cookie: cookie
            }
          }
        });

        var csrfTokenMatch = cookie.match(/csrftoken=(.+);/);
        if (csrfTokenMatch && csrfTokenMatch[1])
          data.options.headers['X-CSRFToken'] = csrfTokenMatch[1];
        data.options.headers['User-Agent'] = $window.navigator.userAgent;

        if (typeof fn !== 'function')
          lastSend = arguments;
        else
          fn = $applyFunc(fn);

        spark.send(ev, data, fn);

        return this;
      };

      /**
       * Cleans up the spark. Removes listeners and
       * nulls references.
       */
      spark.on('end', function cleanup () {
        primus().removeListener('open', openListener);
        spark.removeAllListeners();
        spark = extendedSpark = lastSend = pipeline = null;
      });

      primus().on('open', openListener);

      function openListener () {
        if (lastSend)
          spark.send.apply(spark, lastSend);
      }

      return extendedSpark;
    };

    /**
     * We do not want to intercept
     * transports from primus-emitter,
     * so we let them pass through.
     * @param {Object} response
     * @returns {boolean}
     */
    function isEmitterTransport (response) {
      return response.type === 0 || response.type === 1;
    }

    /**
     * Performs a deep clone of the arguments array-like.
     * @param {Object} args
     * @returns {Array}
     */
    function cloneDeepArguments (args) {
      return _.cloneDeep(_.toArray(args));
    }
  }


  socketModule.factory('$applyFunc', ['$rootScope', $applyFuncFactory]);

  /**
   * Generates an apply HOF.
   * @param {Object} $rootScope
   * @returns {Function}
   */
  function $applyFuncFactory ($rootScope) {
    /**
     * HOF. Returns a function that when called
     * might invoke $apply if we are not in $$phase.
     * @param {Function} func
     * @returns {Function}
     */
    return function $applyFunc (func) {
      return function $innerApplyFunc () {
        var args = arguments;

        if (!$rootScope.$$phase)
          return $rootScope.$apply(apply);
        else
          return apply();

        function apply () {
          return func.apply(null, args);
        }
      };
    };
  }


  socketModule.factory('runPipeline', ['$rootScope', runPipelineFactory]);

  /**
   * Generates a pipeline.
   * @returns {Function}
   */
  function runPipelineFactory () {
    /**
     * When called, recursively iterates the pipeline.
     * If a pipeline function is declared with a next param
     * It is marked as async.
     * @param {Array} pipeline
     * @param {Object} response
     */
    return function next (pipeline, response) {
      if (pipeline.length === 0)
        return;

      var pipe = pipeline[0];
      var nextPipe = _.partial(next, pipeline.slice(1));

      if (pipe.length > 1)
        pipe(response, nextPipe);
      else
        nextPipe(pipe(response));
    };
  }
}());
