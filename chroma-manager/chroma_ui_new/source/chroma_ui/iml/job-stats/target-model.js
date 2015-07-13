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


angular.module('jobStats')
  .factory('TargetModel', ['modelFactory', function (modelFactory) {
    'use strict';

    return modelFactory({
      url: 'target/:id',
      params: { id: '@id' }
    });
  }])
  .factory('TargetMetricModel', ['modelFactory', function (modelFactory) {
    'use strict';

    var TargetMetricModel = modelFactory({
      url: 'target/:id/metric',
      params: { id: '@id' }
    });

    /**
     * Given configuration params, this returns the average of jobs over a time range.
     * Note: this returns a promise, not an instance of TargetMetricModel.
     * @param {Object} params
     * @returns {Object}
     */
    TargetMetricModel.getJobAverage = function getJobAverage (params) {
      return TargetMetricModel.query(params).$promise.then(function then(data) {
        var jobs = _.pluck(data, 'data');

        var sums = jobs.reduce(function (out, obj) {
          Object.keys(obj).forEach(function (key) {
            if (out[key]) {
              out[key].sum += obj[key];
              out[key].count += 1;
            } else {
              out[key] = {
                sum: obj[key],
                count: 1
              };
            }
          });

          return out;
        }, {});

        return Object.keys(sums).reduce(function (out, key) {
          out.push({
            name: key,
            average: sums[key].sum / sums[key].count
          });

          return out;
        }, []);
      });
    };

    return TargetMetricModel;
  }]);
