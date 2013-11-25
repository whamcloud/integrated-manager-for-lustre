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

var inherits = require('util').inherits,
  EventEmitter = require('events').EventEmitter,
  _ = require('lodash');

/**
 * The base datasource that others can extend from.
 * @extends EventEmitter
 * @constructor
 */
function BaseDataSource(conf, request, logger, name) {
  EventEmitter.call(this);

  this.logger = logger.child({channelName: name});

  this.url = conf.apiUrl;
  this.request = request;
  this.options = {url: this.url};
}

inherits(BaseDataSource, EventEmitter);

/**
 * Sets up a poll loop to retrieve new data.
 * @param {Object} options
 */
BaseDataSource.prototype.start = function (options) {
  var self = this;

  // If start is called and we already have a poll loop, kill it.
  if (this.timer) this.stop();

  function startPolling() {
    var params = self.beforeSend(_.cloneDeep(options));

    self.request.get(params, function (err, resp, body) {
      if (err) {
        self.emit('error', {error: err});
      } else if (resp.statusCode >= 400) {
        self.emit('error', {status: resp.statusCode, error: body });
      } else {
        self.transformData(body, done);
      }
    });

    function done (data) {
      self.emit('data', {data: data});
    }
  }

  startPolling();

  this.timer = setInterval(startPolling, 10000);
};

/**
 * Called before every httpRequest. You need to return the options the request should use from this method
 * @param {Object} options
 * @returns {Object}
 */
BaseDataSource.prototype.beforeSend = function (options) {
  return _.defaults(options, this.options);
};

/**
 * Called before the data event is emitted. Override this method to transform the data before it's handed
 * back to the model.
 * @param {*} data
 * @param {Function} done Call this with the transformed data.
 */
BaseDataSource.prototype.transformData = function (data, done) {
  done(data);
};

/**
 * Clears an active poll loop.
 */
BaseDataSource.prototype.stop = function () {
  this.logger.info('stop called.');

  clearInterval(this.timer);

  this.timer = null;
};

module.exports = BaseDataSource;
