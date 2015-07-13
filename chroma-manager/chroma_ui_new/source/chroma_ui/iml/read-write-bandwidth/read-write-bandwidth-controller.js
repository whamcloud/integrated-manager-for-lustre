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


angular.module('readWriteBandwidth', ['charts', 'stream'])
  .controller('ReadWriteBandwidthCtrl',
    ['$scope', 'ReadWriteBandwidthStream', 'DURATIONS', 'formatBytes', ReadWriteBandwidthCtrl]);

function ReadWriteBandwidthCtrl($scope, ReadWriteBandwidthStream, DURATIONS, formatBytes) {
  'use strict';

  $scope.readWriteBandwidth = {
    data: [],
    onUpdate: function onUpdate(unit, size) {
      readWriteBandwidthStream.setDuration(unit, size);
    },
    options: {
      setup: function setup(chart) {
        chart.useInteractiveGuideline(true);

        chart.yAxis.tickFormat(function (number) {
          if (number === 0) return number;

          return formatBytes(Math.abs(number), 3) + '/s';
        });

        chart.isArea(true);

        chart.xAxis.showMaxMin(false);
      }
    },
    unit: DURATIONS.MINUTES,
    size: 10
  };

  var params = $scope.readWriteBandwidthParams || $scope.params || {};

  var readWriteBandwidthStream = ReadWriteBandwidthStream.setup('readWriteBandwidth.data', $scope, params);

  readWriteBandwidthStream.setDuration($scope.readWriteBandwidth.unit, $scope.readWriteBandwidth.size);
}
