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


angular.module('ostBalance', ['charts'])
  .controller('OstBalanceCtrl', ['$scope', 'OstBalanceStream', function OstBalanceCtrl($scope, OstBalanceStream) {
  'use strict';

  $scope.ostBalance = {
    data: [],
    onUpdate: function onUpdate(percentage) {
      ostBalanceStream.setPercentage(percentage);
    },
    options: {
      setup: function(chart, d3) {
        chart.forceY([0, 1]);

        chart.stacked(true);

        chart.yAxis.tickFormat(d3.format('.1%'));

        chart.showXAxis(false);

        chart.tooltip(function(key, x, y, e) {
          var detail = e.point.detail;

          var str = '<h5>' + x + '</h5>\
<p>Free: %(bytesFree)s (%(percentFree)s)</p>\
<p>Used: %(bytesUsed)s (%(percentUsed)s)</p>\
<p>Capacity: %(bytesTotal)s </p>';

          return str.sprintf(detail);
        });
      }
    }
  };

  var ostBalanceStream = OstBalanceStream.setup('ostBalance.data', $scope);

  ostBalanceStream.startStreaming();
}]);
