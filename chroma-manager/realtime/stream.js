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

exports.wiretree = function streamFactory (Q, timers) {
  /**
   * A class used for looping, with a latch function.
   * @param {Number} [interval] number of seconds between polls. Defaults to 10s.
   * @constructor
   */
  function Stream (interval) {
    if (interval == null)
      this.interval = 10000;
    else
      this.interval = interval;
  }

  /**
   * Calling this starts looping.
   * @param {Function} func
   */
  Stream.prototype.start = function start(func) {
    if (this.deferred != null || this.timer != null)
      return;

    this.deferred = Q.defer();

    this.deferred.promise.progress(func);

    var stream = this;

    notify();

    function notify() {
      if (stream.deferred == null)
        return;

      stream.deferred.notify(notifyLoop);
    }

    function notifyLoop() {
      if (stream.deferred == null)
        return;

      stream.timer = timers.setTimeout(notify, stream.interval);
    }
  };

  /**
   * Calling this stops looping.
   */
  Stream.prototype.stop = function stop() {
    if (this.deferred)
      this.deferred.resolve();

    if (this.timer)
      timers.clearTimeout(this.timer);

    this.timer = this.deferred = null;
  };

  return Stream;
};
