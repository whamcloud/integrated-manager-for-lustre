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
  async = require('async'),
  _ = require('lodash');


module.exports = function targetOstMetricsResourceFactory(TargetResource) {
  /**
   * Extension of the TargetResource.
   * Used for joining target names to OST metrics.
   * @constructor
   */
  function TargetOstMetricsResource () {
    TargetResource.call(this);
  }

  inherits(TargetOstMetricsResource, TargetResource);

  /**
   * Gets OST metrics and joins them with their related target name by id.
   * Metrics will be returned with record.name instead of their original key.
   * @param {Object} params
   * @param {Function} cb
   */
  TargetOstMetricsResource.prototype.httpGetOstMetrics = function httpGetOstMetrics(params, cb) {
    var getListParams = {
      qs: {
        kind: 'OST',
        limit: 0
      }
    };

    async.parallel([
      this.httpGetMetrics.bind(this, params),
      this.httpGetList.bind(this, getListParams)
    ], allDone);

    function allDone(err, responses) {
      if (err) {
        cb(err);
        return;
      }

      var metrics = responses[0][1],
        targets = responses[1][1],
        objects = targets.objects;

      var metricsJoinedWithTargets = Object.keys(metrics).reduce(buildMetricsJoinedWithTargets, {});

      function buildMetricsJoinedWithTargets(obj, key) {
        var record = _.find(objects, {id: key});

        if (record)
          obj[record.name] = metrics[key];
        else
          obj[key] = metrics[key];

        return obj;
      }

      cb(null, responses[0][0], metricsJoinedWithTargets, params);
    }
  };

  return TargetOstMetricsResource;
};