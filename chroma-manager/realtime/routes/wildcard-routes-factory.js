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

module.exports = function wildcardRoutesFactory(router, request, loop, logger, _) {
  return function wildcardRoutes () {
    /**
     * Handles all unmatched requests
     * @param {Object} req
     * @param {Object} resp
     */
    router.all('/(.*)', function genericGetHandler (req, resp) {
      var log = logger.child({ path: req.matches[0] });
      log.info('started');
      log.debug(req);

      var makeRequest = request[req.verb].bind(request, req.matches[0], req.data);

      if (resp.ack)
        return makeRequest()
          .then(function ackResponse (response) {
            resp.ack(resp.spark.getResponseFormat(response.statusCode, response.body));
          })
          .catch(function ackError (err) {
            resp.ack(resp.spark.getErrorFormat(err.statusCode || 500, err));
          }).done();

      var cached;

      var finish = loop(function handler (next) {
        makeRequest()
          .then(function writeResponse (response) {
            if (!_.isEqual(response.body, cached))
              resp.spark.writeResponse(response.statusCode, response.body);

            cached = response.body;
          })
          .catch(function writeError (err) {
            resp.spark.writeError(err.statusCode || 500, err);
          })
          .done(next, next);
      }, 1000);

      resp.spark.on('end', function end () {
        resp.spark.removeAllListeners();
        finish();
        finish = null;
        log.info('ended');
      });
    });
  };
};
