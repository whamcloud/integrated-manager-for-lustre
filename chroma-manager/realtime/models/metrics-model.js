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

exports.metricsModelFactory = function (primus, logger) {

  /**
   * starts a new connection for the given channel and datasource
   * @param {String} channelName
   * @param {Function} dataSourceFactory
   */
  return function start(channelName, dataSourceFactory) {
    if (!channelName) throw new Error('A channel name was not provided!');
    if (!dataSourceFactory) throw new Error('A dataSourceFactory was not provided!');

    var metrics = primus.channel(channelName);

    metrics.on('connection', function (spark) {
      logger.info('%s metrics connection.', channelName);

      var dataSource = dataSourceFactory(channelName);

      dataSource.on('data', sendData);

      dataSource.on('error', sendError);

      spark.on('data', data);

      spark.on('end', function disconnect() {
        logger.info('%s end metric spark called.', channelName);

        dataSource.stop();
        dataSource.removeListener('data', sendData);
        dataSource.removeListener('error', sendError);
        dataSource = null;
      });

      /**
       * Uses the options sent from the client to start up the datasource.
       * @param {Object} options
       */
      function data(options) {
        if (!_.isObject(options) || !_.isObject(options.query)) {
          spark.write({
            error: 'options.query not supplied to metricsModel!'
          });

          return;
        }

        logger.info('%s query send from client.', channelName);

        dataSource.start(options);
      }

      /**
       * Writes data from the datasource to the spark.
       * @param {*} value
       */
      function sendData(value) {
        logger.info('%s data sent.', channelName);

        spark.write(value);
      }

      /**
       * Writes an error from the datasource to the spark.
       * @param error
       */
      function sendError(error) {
        logger.error(error);

        spark.write(error);
      }
    });
  };
};
