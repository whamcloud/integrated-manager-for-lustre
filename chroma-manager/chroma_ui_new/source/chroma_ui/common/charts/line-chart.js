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

  angular.module('charts').directive('lineChart', ['moment', 'dateTicks', 'baseChart', lineChart]);

  function lineChart (moment, dateTicks, baseChart) {
    return baseChart({
      generateChart: function generateChart(nv) {
        return nv.models.lineChart();
      },
      onUpdate: function onUpdate(chart, data) {
        if (!Array.isArray(data) || !data[0]) return;

        var values = data[0].values;

        if (!Array.isArray(values)) return;

        var start = values[0].x,
          end = values[values.length - 1].x,
          range = moment(start).twix(end);

        chart.xAxis
          .axisLabel(range.format({implicitYear: false, twentyFourHour: true}))
          .ticks(5)
          .showMaxMin(false)
          .tickFormat(dateTicks.getTickFormatFunc(range));
      }
    });
  }
}());
