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

  angular.module('file-usage', ['charts', 'stream'])
    .controller('FileUsageCtrl', ['$scope', 'streams', 'DURATIONS', 'fileUsageTransformer', FileUsageCtrl]);

  function FileUsageCtrl($scope, streams, DURATIONS, fileUsageTransformer) {
    $scope.fileUsage = {
      data: [],
      unit: DURATIONS.MINUTES,
      size: 10,
      /**
       * Called when the chart duration is changed.
       * @param {String} unit
       * @param {Number} size
       */
      onUpdate: function onUpdate(unit, size) {
        targetMetricStream.start(getParams(unit, size));
      },
      options: {
        /**
         * Sets up the chart.
         * @param {Object} chart The chart object to setup.
         * @param {Object} d3 A d3 instance.
         */
        setup: function setup(chart, d3) {
          chart.useInteractiveGuideline(true);

          chart.forceY([0, 1]);

          chart.yAxis.tickFormat(d3.format('.1%'));

          chart.xAxis.showMaxMin(false);

          chart.color(['#f05b59']);

          chart.isArea(true);
        }
      },
      title: $scope.fileUsageTitle || 'File Usage'
    };

    var transformer = fileUsageTransformer($scope.fileUsageKey || 'Files Used');
    var targetMetricStream = streams.targetStream('fileUsage.data', $scope, 'httpGetMetrics', transformer);
    targetMetricStream.start(getParams($scope.fileUsage.unit, $scope.fileUsage.size));

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
          metrics: 'filestotal,filesfree'
        }
      }, $scope.params || {});
    }
  }

  angular.module('file-usage').factory('fileUsageTransformer', function () {
    return function getTransformer(keyName) {
      return function transformer (resp) {
        if (resp.body.length === 0)
          return resp;

        var dataPoints = [
          {
            key: keyName,
            values: []
          }
        ];

        resp.body = resp.body.reduce(function mungeValues (arr, curr) {
          var date = new Date(curr.ts);

          var value = (curr.data.filestotal - curr.data.filesfree) / curr.data.filestotal;

          dataPoints[0].values.push({
            x: date,
            y: value
          });

          return arr;

        }, dataPoints);

        return resp;
      };
    };
  });
}());