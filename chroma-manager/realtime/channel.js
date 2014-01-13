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

var errorSerializer = require('bunyan/lib/bunyan').stdSerializers.err;

module.exports = function channelFactory (primus, logger, Stream) {
  return function setup(channelName, Resource) {
    var log = logger.child({channelName: channelName});

    log.info('channel %s created with %s resource', channelName, Resource.name);

    var channel = primus.channel(channelName);

    channel.on('connection', function connection(spark) {
      log.info('connected');

      var resource = new Resource(),
        stream = new Stream();

      resource.getHttpMethods().forEach(function (method) {
        spark.on(method, function (params, cb) {
          resource[method](params, function (err, resp, body, reqParams) {
            if (err) {
              log.error({err: err});
              spark.send('streamingError', errorSerializer(err));
            } else {
              var data = {
                headers: resp.headers,
                statusCode: resp.statusCode,
                body: body,
                params: reqParams
              };

              cb(data);
            }
          });
        });
      });

      spark.on('startStreaming', function startStreaming() {
        if (stream.timer) return;

        stream.start(function callback(err) {
          if (err != null) {
            log.error({err: err});
            spark.send('streamingError', errorSerializer(err));
          }

          spark.send('beforeStreaming', function (method, params) {
            log.info('sending request', params);

            resource[method](params, function (err, resp, body, reqParams) {
              if (err != null) {
                log.error({err: err});
                spark.send('streamingError', errorSerializer(err));
                return;
              }

              var data = {
                headers: resp.headers,
                statusCode: resp.statusCode,
                body: body,
                params: reqParams
              };

              spark.send('stream', data);
            });
          });
        });
      });

      spark.on('stopStreaming', function stopStreaming (fn) {
        stream.stop();
        fn('done');
      });

      spark.on('end', function disconnect () {
        spark.removeAllListeners();

        log.info('ended');

        stream.stop();

        stream = null;
        resource = null;
      });
    });
  };
};