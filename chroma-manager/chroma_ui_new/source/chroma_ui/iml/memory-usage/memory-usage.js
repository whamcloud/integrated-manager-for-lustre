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


(function () {
  'use strict';

  angular.module('memory-usage', ['charts', 'stream'])
    .controller('MemoryUsageCtrl',
      ['$scope', 'streams', 'DURATIONS', 'formatBytes', 'memoryUsageTransformer', MemoryUsageCtrl]);

  function MemoryUsageCtrl ($scope, streams, DURATIONS, formatBytes, memoryUsageTransformer) {
    $scope.memoryUsage = {
      data: [],
      unit: DURATIONS.MINUTES,
      size: 10,
      /**
       * Called when the chart duration is changed.
       * @param {String} unit
       * @param {Number} size
       */
      onUpdate: function (unit, size) {
        hostMetricStream.start(getParams(unit, size));
      },
      options: {
        /**
         * Sets up the chart.
         * @param {Object} chart The chart object to setup.
         */
        setup: function(chart) {
          chart.useInteractiveGuideline(true);

          chart.yAxis.tickFormat(function (number) {
            if (number === 0) return number;

            return formatBytes(number, 4);
          });

          chart.xAxis.showMaxMin(false);
        }
      }
    };

    var hostMetricStream = streams.hostStream('memoryUsage.data', $scope, 'httpGetMetrics', memoryUsageTransformer);

    hostMetricStream.start(getParams($scope.memoryUsage.unit, $scope.memoryUsage.size));

    /**
     * Gets the params used by this chart, merged with upstream params.
     * @param {String} unit
     * @param {Number} size
     * @returns {Object}
     */
    function getParams (unit, size) {
      return _.merge({
        qs: {
          unit: unit,
          size: size,
          reduce_fn: 'average',
          metrics: 'mem_MemFree,mem_MemTotal,mem_SwapTotal,mem_SwapFree'
        }
      }, $scope.params || {});
    }
  }

  angular.module('memory-usage').factory('memoryUsageTransformer', [function () {
    return function transformer(resp) {
      if (resp.body.length === 0)
        return resp;

      var dataPoints = [
        { key: 'Total memory', values: [] },
        { key: 'Used memory', values: [] },
        { key: 'Total swap', values: [] },
        { key: 'Used swap', values: [] }
      ];

      resp.body = resp.body.reduce(function mungeValues(arr, curr) {
        var date = new Date(curr.ts);

        dataPoints[0].values.push({
          x: date,
          y: curr.data.mem_MemTotal * 1024
        });

        dataPoints[1].values.push({
          x: date,
          y: curr.data.mem_MemTotal * 1024 - curr.data.mem_MemFree * 1024
        });

        dataPoints[2].values.push({
          x: date,
          y: curr.data.mem_SwapTotal * 1024
        });

        dataPoints[3].values.push({
          x: date,
          y: curr.data.mem_SwapTotal * 1024 - curr.data.mem_SwapFree * 1024
        });

        return arr;

      }, dataPoints);

      return resp;
    };
  }]);
}());
