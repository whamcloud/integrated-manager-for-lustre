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


(function () {
  'use strict';

  angular.module('charts').directive('pieGraph', ['nv', 'baseChart', 'd3', pieGraph]);

  function pieGraph (nv, baseChart, d3) {
    return baseChart({
      directive: {
        link: function (scope, element) {
          var data = [],
            svg = d3.select(element.find('svg')[0]);

          var chart = nv.models.pie()
            .width(20)
            .height(20);

          angular.copy(scope.chartData, data);

          svg
            .datum([data])
            .transition().duration(500)
            .call(chart);

          var deregister = scope.$watch('chartData', function watcher(newVal, oldVal) {
            if (newVal === oldVal) return;

            angular.copy(scope.chartData, data);

            svg
              .transition().duration(500)
              .call(chart);
          }, true);

          scope.$on('$destroy', function onDestroy() {
            deregister();
          });

          return chart;
        }
      }
    });
  }
}());
