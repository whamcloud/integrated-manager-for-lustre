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

module.exports = function testHostRouteFactory (router, request, loop, logger) {
  var jobRegexp = /^\/api\/job\/(\d+)\/$/;

  return function testHostRoute () {
    /**
     * Handles any posts to /test_host.
     * @param {Object} req
     * @param {Object} resp
     */
    router.post('/test_host', function getStatus (req, resp) {
      var log = logger.child({ path: req.matches[0] });
      log.info('started');
      log.debug(req);

      var cached, commandPromise;

      var finish = loop(function handler (next) {
        commandPromise = (commandPromise ? commandPromise.then(askAgain) : request.post('/test_host', req.data));
        commandPromise = commandPromise.then(transformCommand);

        commandPromise
          .then(getJobsOrUndefined)
          .then(function writeResponseIfFinished (response) {
            if (!response) return;

            response.body.objects = response.body.objects.map(function normalize (job) {
              return job.step_results[job.steps[0]];
            });

            if (!_.isEqual(response.body, cached))
              resp.spark.writeResponse(response.statusCode, response.body);

            cached = response.body;
            commandPromise = null;
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

  /**
   * Given some command info, asks for a newer representation of the command.
   * @param {Object} commandInfo
   * @returns {Object}
   */
  function askAgain (commandInfo) {
    return request.get('/command', {
      qs: {
        id__in: commandInfo.ids,
        limit: 0
      }
    });
  }

  /**
   * Returns jobs if the command has finished,
   * otherwise undefined
   * @param {Object} commandInfo
   * @returns {Object|undefined}
   */
  function getJobsOrUndefined (commandInfo) {
    if (commandInfo.finished)
      return request.get('/job', {
        jsonMask: 'objects(step_results,steps)',
        qs: {
          id__in: commandInfo.jobIds,
          limit: 0
        }
      });
  }

  /**
   * Pulls the job id from a resource uri.
   * @param {String} jobUri
   * @returns {String}
   */
  function extractIds (jobUri) {
    return jobUri.match(jobRegexp)[1];
  }

  /**
   * Given a generic command response, transforms it to
   * something useful to the pipeline.
   * @param {Object} response
   * @returns {{finished: boolean, ids: Array, jobIds: Array}}
   */
  function transformCommand (response) {
    var finished = _(response.body.objects)
        .map(pickStatuses)
        .map(_.values)
        .flatten()
        .compact()
        .size() === response.body.objects.length;

    var ids = _.pluck(response.body.objects, 'id');

    var jobIds = _(response.body.objects)
      .pluck('jobs')
      .flatten()
      .map(extractIds)
      .value();

    return {
      finished: finished,
      ids: ids,
      jobIds: jobIds
    };
  }

  /**
   * Given some commands, picks status properties
   * @param {Array} commands
   * @returns {Array}
   */
  function pickStatuses (commands) {
    return _.pick(commands, ['cancelled', 'complete', 'errored']);
  }
};
