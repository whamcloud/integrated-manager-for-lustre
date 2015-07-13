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


(function () {
  'use strict';

  angular.module('cpu-usage', ['charts', 'stream'])
    .controller('CpuUsageCtrl', ['$scope', 'streams', 'DURATIONS', 'cpuUsageTransformer', CpuUsageController]);

  function CpuUsageController($scope, streams, DURATIONS, cpuUsageTransformer) {
    $scope.cpuUsage = {
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
         * @param {Object} d3 A d3 instance.
         */
        setup: function(chart, d3) {
          chart.useInteractiveGuideline(true);

          chart.forceY([0, 1]);

          chart.yAxis.tickFormat(d3.format('.1%'));

          chart.xAxis.showMaxMin(false);

          chart.color(['#2f7087', '#f09659', '#f0d359']);
        }
      }
    };

    var hostMetricStream = streams.hostStream('cpuUsage.data', $scope, 'httpGetMetrics', cpuUsageTransformer);
    hostMetricStream.start(getParams($scope.cpuUsage.unit, $scope.cpuUsage.size));

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
          metrics: 'cpu_total,cpu_user,cpu_system,cpu_iowait'
        }
      }, $scope.params || {});
    }
  }

  angular.module('cpu-usage').factory('cpuUsageTransformer', cpuUsageTransformer);

  function cpuUsageTransformer () {
    /**
     * Takes a metrics response and transforms the values.
     * @param {object} resp The server response.
     */
    return function transformer(resp) {
      var newVal = resp.body;

      if (newVal.length === 0) return resp;

      var dataPoints = [
        { key: 'user', values: [] },
        { key: 'system', values: [] },
        { key: 'iowait', values: [] }
      ];

      resp.body = newVal.reduce(function mungeValues(arr, curr) {
        var date = new Date(curr.ts);

        arr.forEach(function (series) {
          var value = ((100 * curr.data['cpu_' + series.key] + (curr.data.cpu_total / 2)) / curr.data.cpu_total) / 100;
          series.values.push({
            x: date,
            y: value
          });
        });

        return arr;

      }, dataPoints);

      return resp;
    };
  }
}());

