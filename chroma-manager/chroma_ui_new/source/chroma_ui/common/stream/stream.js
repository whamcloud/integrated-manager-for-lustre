//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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

  angular.module('stream').factory('stream', ['$parse', '$q', 'primus', 'pageVisibility', streamFactory]);

  function streamFactory($parse, $q, primus, pageVisibility) {
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
        this.channel = primus().channel(channelName);

        scope.$on('$destroy', function destroy() {
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
       */
      Stream.prototype.startStreaming = function startStreaming (params, streamMethod) {
        var cloned = _.cloneDeep(this.defaultParams),
          scope = this.scope,
          merged = _.merge(cloned, params),
          self = this;

        var transformers = this.generateTransformProcessor(defaults.transformers);

        this.channel.on('stream', function (resp) {
          scope.$apply(function $apply() {
            transformers(resp);
          });
        });

        this.channel.on('streamingError', function handleError(err) {
          scope.$apply(function $apply() {
            console.log(err);
          });
        });

        this.channel.on('beforeStreaming', function (cb) {
          scope.$apply(function $apply() {
            self.beforeStreaming(streamMethod || defaultStreamMethod, merged, cb);
          });
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
          scope.$apply(function $apply () {
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
       * Returns a function that when called recursively iterates the list.
       * Each transformer has Stream as a context.
       * @param {array} queue
       * @returns function
       */
      Stream.prototype.generateTransformProcessor = function generateTransformProcessor(queue) {
        queue = queue.map(function bindTransformers(transformer) {
          return _.bind(transformer, this);
        }, this);

        return function processTransform(newVal, index) {
          index = (index == null ? 0 : index);

          if (index === queue.length) return;

          var deferred = $q.defer();

          queue[index](newVal, deferred);

          index += 1;

          deferred.promise.then(function (data) { processTransform(data, index); });
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

        this.channel.end();
        this.channel = null;
        this.scope = null;
        this.getter = null;
      };

      return Stream;
    };
  }
}());