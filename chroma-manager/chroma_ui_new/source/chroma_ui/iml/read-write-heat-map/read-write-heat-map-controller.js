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


angular.module('readWriteHeatMap', ['charts', 'stream'])
  .controller('ReadWriteHeatMapCtrl',
    ['$scope', 'd3', 'ReadWriteHeatMapStream', 'DURATIONS', 'formatBytes', ReadWriteHeatMapCtrl]);

function ReadWriteHeatMapCtrl($scope, d3, ReadWriteHeatMapStream, DURATIONS, formatBytes) {
  'use strict';

  $scope.readWriteHeatMap = {
    data: [],
    onUpdate: function (unit, size) {
      $scope.readWriteHeatMap.data.length = 0;

      var params = {
        qs: {
          unit: unit,
          size: size
        }
      };

      readWriteHeatMapStream.restart(params);
    },
    options: {
      setup: function(chart) {
        chart.options({
          showYAxis: false,
          formatter: formatter,
          margin: { left: 50 }
        });

        chart.onMouseOver(mouseHandler(function (d) {
          return {
            date: d.x,
            ostName: d.key,
            bandwidth: formatter(d.z)
          };
        }));

        chart.onMouseMove(mouseHandler());

        chart.onMouseOut(mouseHandler(function () {
          return {
            isVisible: false
          };
        }));

        chart.xAxis().showMaxMin(false);
      }
    },
    type: ReadWriteHeatMapStream.TYPES.READ,
    TYPES: ReadWriteHeatMapStream.TYPES,
    toggle: function (type) {
      $scope.readWriteHeatMap.data.length = 0;

      readWriteHeatMapStream.type = type;
      readWriteHeatMapStream.restart();
    },
    unit: DURATIONS.MINUTES,
    size: 10
  };

  var readWriteHeatMapStream = ReadWriteHeatMapStream.setup('readWriteHeatMap.data', $scope, {
    qs: {
      unit: $scope.readWriteHeatMap.unit,
      size: $scope.readWriteHeatMap.size
    }
  });

  readWriteHeatMapStream.type = ReadWriteHeatMapStream.TYPES.READ;
  readWriteHeatMapStream.startStreaming();

  function formatter (z) {
    return formatBytes(z, 3) + '/s';
  }

  function mouseHandler (overrides) {
    if (!_.isFunction(overrides))
      overrides = _.iterators.K({});

    return function (d) {
      $scope.$apply(function () {
        _.extend($scope.readWriteHeatMap, {
          isVisible: true,
          x: (d3.event.hasOwnProperty('offsetX') ? d3.event.offsetX : d3.event.layerX) + 50,
          y: (d3.event.hasOwnProperty('offsetY') ? d3.event.offsetY : d3.event.layerY) + 50
        }, overrides(d));
      });
    };
  }
}
