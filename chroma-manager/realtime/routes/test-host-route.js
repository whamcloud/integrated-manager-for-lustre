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

exports.wiretree = function testHostRouteWrapper (router, request, loop, logger, Q, _) {
  var jobRegexp = /^\/api\/job\/(\d+)\/$/;

  return function testHostRoute () {
    /**
     * Given some command info, asks for a newer representation of the command.
     * @param {Object} headers
     * @param {Array} ids
     * @returns {Object}
     */
    var askAgain = _.curry(function askAgain (headers, ids) {
      return request.get('/command', {
        qs: {
          id__in: ids,
          limit: 0
        },
        headers: headers
      });
    });

    /**
     * Returns jobs if the command has finished,
     * otherwise undefined
     * @param {Object} headers
     * @param {Boolean} finished
     * @param {Array} jobIds
     * @returns {Object|undefined}
     */
    var getJobsOrUndefined = _.curry(function getJobsOrUndefined (headers, finished, jobIds) {
      if (finished)
        return request.get('/job', {
          jsonMask: 'objects(step_results,steps)',
          qs: {
            id__in: jobIds,
            limit: 0
          },
          headers: headers
        });
    });

    /**
     * Handles any posts to /test_host.
     * @param {Object} req
     * @param {Object} resp
     */
    router.post('/test_host', function getStatus (req, resp) {
      var log = logger.child({ path: req.matches[0] });
      log.info('started');
      log.debug(req);

      var cached, pendingCommandPromise;

      var headers = req.data.headers || {};

      var ifExists = _.if(_.exists);

      var finish = loop(function handler (next) {
        var objectsPromise;

        if (pendingCommandPromise)
          objectsPromise = pendingCommandPromise
            .then(askAgain(headers));
        else
          objectsPromise = request.post('/test_host', req.data)
            .then(_.unwrapResponse(_.fmapProp('command')));

        objectsPromise = objectsPromise.then(function (response) {
          return response.body.objects;
        });

        var isCommandFinishedPromise = objectsPromise
          .then(_.fmapProps(['cancelled', 'complete', 'errored']))
          .then(_.fmap(_.values))
          .then(_.fmap(_.any))
          .then(_.flatten)
          .then(_.every);

        pendingCommandPromise = objectsPromise.then(_.fmapProp('id'));

        var jobIds = objectsPromise
          .then(_.fmapProp('jobs'))
          .then(_.flatten)
          .then(_.fmap(extractIds));

        Q.all([isCommandFinishedPromise, jobIds])
          .spread(getJobsOrUndefined(headers))
          .then(ifExists(_.unwrapResponse(_.fmap(function (job) {
            return job.step_results[job.steps[0]];
          }))))
          .then(ifExists(function writeResponseIfFinished (response) {
            if (!_.isEqual(response.body, cached))
              resp.spark.writeResponse(response.statusCode, response.body);

            cached = response.body;
            pendingCommandPromise = null;
          }))
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

  /**
   * Pulls the job id from a resource uri.
   * @param {String} jobUri
   * @returns {String}
   */
  function extractIds (jobUri) {
    return jobUri.match(jobRegexp)[1];
  }
};
