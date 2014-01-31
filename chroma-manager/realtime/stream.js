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


'use strict';

var _ = require('lodash');

module.exports = function streamFactory(logger) {
  /**
   * Sets up a loop.
   * @constructor
   */
  function Stream(interval) {
    this.interval = interval || 10000;
  }

  /**
   * Stop streaming.
   */
  Stream.prototype.stop = function stop () {
    clearTimeout(this.timer);

    this.timer = null;
  };

  /**
   * Starts streaming a passed resource method every interval.
   * Only one stream can be running on an instance.
   * @param {function (?Object, Function)} cb
   */
  Stream.prototype.start = function start(cb) {
    var self = this,
      partialCb = _.partialRight(cb, done);

    if (this.timer) {
      var err = new Error('Already streaming.');

      logger.error({err: err});
      partialCb({error: err});
      return;
    }

    partialCb(null);

    function done() {
      self.timer = setTimeout(function (err) {
        if (self.timer == null)
          return;

        partialCb(err);
      }, self.interval);
    }
  };

  return Stream;
};