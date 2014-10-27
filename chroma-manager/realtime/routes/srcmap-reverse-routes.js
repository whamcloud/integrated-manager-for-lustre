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

exports.wiretree = function srcmapReverseRoutesWrapper (router, request, logger, srcmapReverse, promisedFile, conf) {
  return function srcmapReverseRoutes() {

    router.post('/srcmap-reverse', function srcmapReverseHandler (req, resp) {
      logger.info('srcmap-reverse req rcvd');

      promisedFile.getFile(conf.sourceMapDir)
        .then(function reverseTrace (sourceMapFile) {
          return srcmapReverse.execute(req.data.stack, sourceMapFile);
        })
        .catch(function handleErr (err) {
          resp.ack(resp.spark.getErrorFormat(500, err));

          throw err;
        })
        .then(function ackStack (reversed) {
          resp.ack(resp.spark.getResponseFormat(201, { data: reversed }));

          req.data.stack = reversed;

          return req;
        })
        .then(function sendRequest (req) {
          var headers = req.data.headers;
          delete req.data.headers; // Move the headers out of the data property.

          // Call out to the api to create/add to the client_errors.log file.
          return request.post('client_error/',{
            json: req.data,
            headers: headers
          });

        })
        .catch(function doNothing () { })
        .done();
    });
  };
};
