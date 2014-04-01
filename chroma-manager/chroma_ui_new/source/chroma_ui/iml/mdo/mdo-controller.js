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


angular.module('mdo', ['charts', 'stream'])
  .controller('MdoCtrl', ['$scope', 'MdoStream', 'DURATIONS', function MdoCtrl($scope, MdoStream, DURATIONS) {
  'use strict';

  $scope.mdo = {
    data: [],
    unit: DURATIONS.MINUTES,
    size: 10,
    onUpdate: function (unit, size) {
      mdoStream.setDuration(unit, size);
    },
    options: {
      setup: function(chart, d3) {
        var rounder = d3.format('.2r'),
          percentage = d3.format('.1%');

        chart.useInteractiveGuideline(true);

        //@FIXME: Hack, remove when https://github.com/novus/nvd3/pull/313 lands.
        function valueFormatter(d) {
          return (chart.stacked.style() === 'expand' ? percentage(d): Math.round(d));
        }
        chart.interactiveLayer.tooltip.valueFormatter(valueFormatter);

        chart.interactiveLayer.tooltip.valueFormatter = angular.identity(function() {
          if (!arguments.length) return valueFormatter;

          return chart.interactiveLayer.tooltip;
        });

        chart.yAxis.tickFormat(function (number) {
          var thousands = number / 1000;

          if (thousands >= 1) number = rounder(thousands) + 'K';

          return number;
        });

        chart.forceY([0, 1]);

        chart.xAxis.showMaxMin(false);
      }
    }
  };

  var mdoStream = MdoStream.setup('mdo.data', $scope, $scope.params || {});

  mdoStream.setDuration($scope.mdo.unit, $scope.mdo.size);
}]);
