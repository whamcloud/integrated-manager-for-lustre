//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

var through = require('through');
var apiRequest = require('../request/api');
var _ = require('lodash-mixins');
var λ = require('highland');

exports.getCommands = _.curry(function getCommand (req) {
  var objects;

  // requests commands, only returns
  // values when all are finished.
  return apiRequest('/command', req)
    .pluck('objects')
    .tap(function (x) {
      objects = x;
    })
    .flatten()
    .through(through.pluckValues(['cancelled', 'complete', 'errored']))
    .map(_.some)
    .through(through.every)
    .compact()
    .map(function returnObjects () {
      return objects;
    })
    .flatten();
});

var jobRegexp = /^\/api\/job\/(\d+)\/$/;

exports.getSteps = _.curry(function getSteps (s) {
  return s
    .pluck('jobs')
    .flatten()
    .invoke('match', [jobRegexp])
    .map(λ.get(1))
    .through(through.collectValues)
    .flatMap(function getJobs (ids) {
      return apiRequest('/job', {
        qs: {
          id__in: ids,
          limit: 0
        },
        jsonMask: 'objects(step_results,steps)'
      });
    })
    .pluck('objects')
    .flatten()
    .map(function getSteps (job) {
      return job.step_results[job.steps[0]];
    });
});
