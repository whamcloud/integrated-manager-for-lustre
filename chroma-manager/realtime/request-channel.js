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

/**
 * A channel to make routed requests over
 * @param {Object} primus
 * @param {Object} router
 * @param {Function} routes
 * @param {Object} logger
 * @param {Function} requestChannelValidator
 * @returns {Object}
 */
module.exports = function requestChannelFactory (primus, router, routes, logger, requestChannelValidator) {
  /**
   * Inner factory.
   * @returns {Object}
   */
  return function requestChannel () {
    routes();

    var channel = primus.channel('request');

    channel.on('connection', function onConnection (spark) {
      spark.on('req', function onData (data, ack) {
        logger.info('got data', data);

        var ackOrWriteError = ackOrWriteErrorFactory(spark, ack);
        var errors = requestChannelValidator(data);

        if (errors.length)
          return ackOrWriteError(400, new Error(errors));

        var options = data.options || {};
        var method = (typeof options.method !== 'string' ? 'get' : options.method);

        try {
          router.go(data.path, method, spark, options, ack);
        } catch (e) {
          ackOrWriteError(400, e);
        }
      });
    });

    return channel;
  };

  /**
   * HOF. Given a spark, and ack determines the correct one
   * to write to and does it.
   * @param {Object} spark
   * @param {Function} [ack]
   * @returns {Function}
   */
  function ackOrWriteErrorFactory (spark, ack) {
    /**
     * Writes an error or status code over the spark.
     * @param {Number} status
     * @param {Error} error
     */
    return function ackOrWriteError (status, error) {
      if (ack)
        ack(spark.getErrorFormat(status, error));
      else
        spark.writeError(status, error);
    };
  }
};
