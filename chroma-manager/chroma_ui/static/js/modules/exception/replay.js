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


(function (_) {
  'use strict';

  angular.module('exception').factory('replay', ['$http', '$q', function ($http, $q) {
    /**
     * This class is responsible for adding and running a queue of request configs that failed due to a 0 status code.
     * The 0 status code is a good indication that the backend server is down.
     * @constructor
     */
    function Replay() {
      this._pending = [];
    }

    /**
     * Checks if the passed config contains an idempotent method.
     * We cannot guarantee replay order 100% so we only want to replay idempotent methods.
     *
     * @param {object} config The config to inspect.
     * @throws {error} Throws if the config was not structured as expected.
     * @returns {boolean} Was the method idempotent?
     */
    Replay.prototype.isIdempotent = function isIdempotent(config) {
      var idempotentVerbs = ['GET', 'PUT', 'DELETE'];

      if (!config || !config.method) throw new Error('Config passed to isIdempotent not structured as expected!');

      return idempotentVerbs.indexOf(config.method) !== -1;
    };

    /**
     * Adds the $http config object to the queue of pending ones.
     *
     * @param {object} config
     * @throws {error} Throws if the method passed was not idempotent.
     * @returns {object} A promise that is resolved when the associated config completes, or is rejected when
     * it returns with a failed non 0 status code.
     */
    Replay.prototype.add = function add(config) {
      if (!this.isIdempotent(config)) throw new Error('Idempotent verb not passed in the config!');

      var deferred = $q.defer();

      this._pending.push({
        config: config,
        deferred: deferred
      });

      return deferred.promise;
    };

    /**
     * Runs the queue of pending replays.
     * The next replay is not called until the previous one is resolved or rejected with a non 0 status.
     * Upon resolution or rejection with a non 0 status, the config is spliced from the queue.
     *
     * @returns {object} A promise representing the completion state of the pending replays.
     */
    Replay.prototype.go = function go() {
      var self = this,
        deferred = $q.defer();

      deferred.resolve();

      return _.clone(this._pending).reduce(function reduce(promise, item) {
        item.config.UI_REPLAY = true;

        return promise.then(function success() {
          return $http(item.config).then(function httpSuccess(resp) {
            spliceItem(item);

            item.deferred.resolve(resp);

            return resp;
          }, function httpErr(resp) {
            var rejected = $q.reject(resp);

            if (resp.status === 0) return rejected;

            spliceItem(item);

            item.deferred.reject(resp);

            return rejected;
          });
        });
      }, deferred.promise);

      function spliceItem(item) {
        var itemIndex = self._pending.indexOf(item);

        self._pending.splice(itemIndex, 1);
      }
    };

    var replay = new Replay();

    /**
     * Does the queue have any items pending?
     *
     * @methodOf Replay
     * @name hasPending
     * @returns {boolean} Returns true if the queue has any items pending.
     */
    Object.defineProperty(replay, 'hasPending', {
      get: function () { return replay._pending.length > 0; }
    });

    return replay;
  }]);
}(window.lodash));
