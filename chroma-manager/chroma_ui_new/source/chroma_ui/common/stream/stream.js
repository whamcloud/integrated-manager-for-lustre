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

  angular.module('stream').factory('stream',
    ['$parse', '$q', '$document', '$exceptionHandler', 'primus', 'pageVisibility', streamFactory]);

  function streamFactory($parse, $q, $document, $exceptionHandler, primus, pageVisibility) {
    return function getStream(channelName, defaultStreamMethod, defaults) {
      defaults = _.merge({
        params: {},
        transformers: []
      }, defaults);

      /**
       * This class represents a continuous stream of data.
       * @param {String} expression
       * @param {Object} scope
       * @param {Object} params
       * @constructor
       */
      function Stream (expression, scope, params) {
        var self = this,
          parsed = $parse(expression);

        var clonedDefaultParams = _.cloneDeep(defaults.params);

        this.scope = scope;
        this.defaultParams = _.merge(clonedDefaultParams, params);
        this.getter = _.partial(parsed, scope);
        this.setter = _.partial(parsed.assign, scope);
        this.channel = primus().channel(channelName);

        this.removeDestroyListener = scope.$on('$destroy', function destroy() {
          self.end();
        });
      }

      /**
       * A convenience for getting a new stream.
       * @param {String} expression
       * @param {Object} scope
       * @param {Object} params
       * @returns {Stream}
       */
      Stream.setup = function setup(expression, scope, params) {
        return new Stream(expression, scope, params);
      };

      /**
       * Starts the stream
       * @param {Object} [params] These will be merged with the default params.
       * @param {String} [streamMethod] The method to stream from.
       * @param {Array|function} [prependTransformers] Transformers to append.
       */
      Stream.prototype.startStreaming = function startStreaming (params, streamMethod, prependTransformers) {
        var cloned = _.cloneDeep(this.defaultParams),
          scope = this.scope,
          merged = _.merge(cloned, params),
          self = this;

        if (typeof prependTransformers === 'function')
          prependTransformers = [prependTransformers];

        var transformersList = (prependTransformers || []).concat(defaults.transformers);

        var transformers = this.generateTransformProcessor(transformersList);

        this.channel.on('stream', function (resp) {
          localApply(scope, function runTransformers() {
            transformers(resp);
          });
        });

        this.channel.on('streamingError', function handleError(err) {
          localApply(scope, function handleStreamingError() {
            $exceptionHandler(err);

            self.end();
          });
        });

        this.channel.on('beforeStreaming', function (callback) {
          localApply(scope, function handleBeforeStreaming() {
            self.beforeStreaming(streamMethod || defaultStreamMethod, merged, callbackWithAuth);
          });

          /**
           * Adds auth to the params.
           * @param {String} method The remote method to invoke.
           * @param {Object} params The params to pass to the remote method.
           */
          function callbackWithAuth (method, params) {
            params = _.merge({}, params, {
              headers: {
                Cookie: $document[0].cookie
              }
            });

            callback(method, params);
          }
        });

        function start () {
          self.channel.send('startStreaming');
        }

        start();

        this._removeOpenListener = function removeOpenListener() {
          primus().removeListener('open', start);
        };

        primus().on('open', start);

        this._removePageVisibilityListener = pageVisibility.onChange(function (isHidden) {
          localApply(scope, function toggleVisibility () {
            if (isHidden) {
              self.channel.send('stopStreaming');
            } else {
              start();
            }
          });
        });
      };

      /**
       * Called before every stream request on the backend.
       * You can update params or method here.
       * @param {String} method
       * @param {Object} params
       * @param {Function} cb
       */
      Stream.prototype.beforeStreaming = function beforeStreaming(method, params, cb) {
        cb(method, params);
      };

      /**
       * Stops the current stream and removes listeners.
       * @param {Function} cb Called when the stream has been stopped.
       */
      Stream.prototype.stopStreaming = function stopStreaming (cb) {
        this.channel.send('stopStreaming', cb);
        this.channel.removeAllListeners('stream')
          .removeAllListeners('beforeStreaming')
          .removeAllListeners('streamingError');

        if (typeof this._removeOpenListener === 'function')
          this._removeOpenListener();

        if(typeof this._removePageVisibilityListener === 'function')
          this._removePageVisibilityListener();
      };

      /**
       * Restarts the stream with new params.
       * @param {Object} [params]
       */
      Stream.prototype.updateParams = function updateParams (params) {
        var self = this;

        this.stopStreaming(function callback() {
          self.startStreaming(params);
        });
      };

      /**
       * Alias to to updateParams
       * @type {updateParams}
       */
      Stream.prototype.restart = Stream.prototype.updateParams;

      /**
       * Returns a function that when called iterates the list.
       * Each transformer has Stream as a context.
       * @param {Array} queue
       * @returns {function}
       */
      Stream.prototype.generateTransformProcessor = function generateTransformProcessor(queue) {
        if (!Array.isArray(queue))
          queue = [queue];

        queue = queue.map(function bindTransformers(transformer) {
          return _.bind(transformer, this);
        }, this);

        return function processTransform(val) {
          queue.reduce(function iterator (promise, transformer) {
            return promise.then(function then(val) {
              return transformer(val);
            });
          }, $q.when(val));
        };
      };

      /**
       * Ends the stream and nulls all references.
       * Call this when you are finished with the stream.
       */
      Stream.prototype.end = function end () {
        if (typeof this._removeOpenListener === 'function')
          this._removeOpenListener();

        if(typeof this._removePageVisibilityListener === 'function')
          this._removePageVisibilityListener();


        this.removeDestroyListener();
        this.removeDestroyListener = null;

        this.channel.end();
        this.channel = null;
        this.scope = null;
        this.getter = null;
        this.setter = null;
      };

      return Stream;
    };

    function localApply(scope, expr) {
      try {
        return scope.$eval(expr);
      } catch (e) {
        $exceptionHandler(e);
      } finally {
        try {
          scope.$digest();
        } catch (e) {
          $exceptionHandler(e);
          throw e;
        }
      }
    }
  }

  angular.module('stream').factory('beforeStreamingDuration', ['getServerMoment', function (getServerMoment) {
    return function beforeStreaming(method, params, makeRequest) {
      if (!params.qs || !params.qs.unit)
        return makeRequest(method, params);

      var end = getServerMoment().milliseconds(0);

      params.qs.end = end.toISOString();
      params.qs.begin = end.subtract(params.qs.size, params.qs.unit).toISOString();

      makeRequest(method, params);
    };
  }]);

  angular.module('immutableStream', []).factory('immutableStream', [immutableStreamFactory]);

  /**
   * This wraps a stream and makes it immutable.
   * This means that once a stream has started, you can no longer
   * stop streaming and then restart on the same channel.
   * Now, when a stream is changed a new channel is created and used instead.
   * This is a stopgap in a longer term move to simplify the interface between the client and server.
   * @returns {function}
   */
  function immutableStreamFactory () {
    /**
     * Captures a Stream and makes it immutable.
     * @param {Stream} Stream A Stream type
     * @param {string} expression The expression to databind on the scope
     * @param {object} $scope The scope to data bind to.
     * @param {string} [streamMethod] The method to stream on.
     * @param {function|array} [transformers] Transformers to call.
     * @returns {{start: create, end: end}} A simple interface to start and end a stream instance.
     */
    return function getStream (Stream, expression, $scope, streamMethod, transformers) {
      var streamInstance;

      return {
        start: function start(params) {
          this.end();

          streamInstance = Stream.setup(expression, $scope);
          streamInstance.startStreaming(params, streamMethod, transformers);
        },
        end: function end() {
          if (streamInstance)
            streamInstance.end();

          streamInstance = null;
        }
      };
    };
  }

  angular.module('streams', ['immutableStream', 'host', 'target', 'fileSystem']).factory('streams',
    ['immutableStream', 'HostStream', 'TargetStream', 'FileSystemStream', streamsFactory]);

  /**
   * This wraps streams as immutable and exposes an object of streams.
   * An object is returned to keep our dependencies short.
   * @param {object} immutableStream
   * @param {function} HostStream
   * @param {function} TargetStream
   * @param {function} FileSystemStream
   * @returns {{hostStream: function, targetStream: function}}
   */
  function streamsFactory (immutableStream, HostStream, TargetStream, FileSystemStream) {
    return {
      hostStream: getStream(HostStream),
      targetStream: getStream(TargetStream),
      fileSystemStream: getStream(FileSystemStream)
    };

    /**
     * This captures a stream and returns a function that creates an immutable stream when invoked.
     * @param {function} Stream
     * @returns {function}
     */
    function getStream (Stream) {
      return function createStream () {
        var args = _.toArray(arguments);

        args.unshift(Stream);

        return immutableStream.apply(immutableStream, args);
      };
    }
  }
}());