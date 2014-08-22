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
    .factory('socket', ['$applyFunc', '$document', 'primus', 'runPipeline', socketFactory]);

  /**
   * Generates a new socket.
   * @param {Function} $applyFunc
   * @param {Object} $document
   * @param {Function} primus
   * @param {Function} runPipeline
   * @returns {Object}
   */
  function socketFactory ($applyFunc, $document, primus, runPipeline) {
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
        var $apply = $applyFunc(function handler () {
          extendedSpark.lastArgs = arguments;

          fn.apply(context, extendedSpark.lastArgs);
        });

        spark.on(event, $apply, context);

        return function off () {
          spark.removeListener(event, $apply);
        };
      };

      /**
       * This acts like a Bacon property. It looks for last arg and if available, emits
       * immediately.
       * @param {String} event
       * @param {Function} fn
       * @param {Object} context
       * @returns {Function}
       */
      extendedSpark.onValue = $applyFunc(function onValue (event, fn, context) {
        if (extendedSpark.lastArgs)
          fn.apply(context, extendedSpark.lastArgs);

        return extendedSpark.on(event, fn, context);
      });

      var pipeline = [function emitPipeline (response) {
        spark.emit('pipeline', response);
      }];

      /**
       * Adds a new pipe into the pipeline
       * @param {Function} pipe
       * @returns {Object}
       */
      extendedSpark.addPipe = function addPipe (pipe) {
        pipeline.splice(-1, 0, pipe);

        if (pipeline.length === 2)
          extendedSpark.on('data', function run (response) {
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
        data = _.merge({}, data, {
          options: {
            headers: {
              Cookie: $document[0].cookie
            }
          }
        });

        if (typeof fn !== 'function')
          lastSend = arguments;

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


