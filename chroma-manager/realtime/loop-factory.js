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

var _ = require('lodash');

module.exports = function loopFactory (timers) {
  var DEFAULT_INTERVAL = 1000;

  /**
   * HOF. Given a function and an interval
   * returns a loop object.
   * The loop can be started and finished.
   * Once finished, the loop cannot be restarted.
   * @param {Function} func
   * @param {Number} [interval]
   * @returns {Function}
   */
  return function create (func, interval) {
    var handles = {
      start: function start () {
        if (this.finished) return;

        var next = start.bind(this);
        var handler = _.partial(func, next);
        this.timer = timers.setTimeout(handler, interval || DEFAULT_INTERVAL);
      },
      finish: function finish () {
        if (this.timer != null)
          timers.clearTimeout(this.timer);

        this.timer = null;
        this.finished = true;
      }
    };

    func(handles.start.bind(handles));

    return handles.finish.bind(handles);
  };
};

