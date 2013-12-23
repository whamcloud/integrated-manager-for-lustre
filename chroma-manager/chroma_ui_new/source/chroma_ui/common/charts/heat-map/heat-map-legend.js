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

  angular.module('charts').factory('heatMapLegendFactory',
    ['d3', 'chartUtils', 'raf', heatMapLegendFactory]);

  function heatMapLegendFactory (d3, chartUtils, raf) {
    var TEXT_PADDING = 5,
      STEP_WIDTH = 1,
      MIN = 0,
      MAX = 100;

    var translator = chartUtils.translator,
      cl = chartUtils.cl,
      getBBox = chartUtils.getBBox,
      chartParamMixins = chartUtils.chartParamMixins;

    return function getLegend() {
      var config = {
        margin: {top: 5, right: 0, bottom: 5, left: 0},
        width: 200,
        height: 30,
        formatter: _.identity,
        lowColor: '#fbeCeC',
        highColor: '#d9534f',
        rightAlign: true,
        legendScale: d3.scale.linear()
      };

      chartParamMixins(config, chart);

      function chart (selection) {
        var margin = chart.margin(),
          width = chart.width(),
          height = chart.height(),
          formatter = chart.formatter(),
          legendScale = chart.legendScale();

        selection.each(function(data) {
          var elRefs = {};

          elRefs.container = d3.select(this);

          var values = _.pluck(data, 'values'),
            mergedValues = d3.merge(values);

          if (mergedValues.length === 0)
            return;

          var domain = d3.extent(mergedValues, function (d) { return d.z; });

          if (domain[0] === domain[1])
            return;

          legendScale.domain([MIN, MAX]).range([chart.lowColor(), chart.highColor()]);

          var availableWidth = width - margin.left - margin.right,
            availableHeight = height - margin.top - margin.bottom;

          var LEGEND_SEL = 'nv-legend',
            MIN_SEL = 'min',
            STEPS_SEL = 'steps',
            STEP_SEL = 'step',
            MAX_SEL = 'max';

          //data join.
          elRefs.wrap = elRefs.container.selectAll(cl(LEGEND_SEL)).data([legendScale.ticks(100)]);

          // setup structure on enter.
          elRefs.gEnter = elRefs.wrap.enter().append('g').attr('class', LEGEND_SEL);

          elRefs.gEnter.append('text').attr('class', MIN_SEL);
          var stepsGEnter = elRefs.gEnter.append('g').attr('class', STEPS_SEL);
          elRefs.gEnter.append('text').attr('class', MAX_SEL);

          stepsGEnter.append('rect')
            .attr('x', 0)
            .attr('fill', 'white')
            .attr('height', 11)
            .attr('width', 101)
            .attr('stroke', '#CCC');

          // These operate on enter + update.
          elRefs.minText = elRefs.wrap.select(cl(MIN_SEL));
          elRefs.stepsGroup = elRefs.wrap.select(cl(STEPS_SEL));
          elRefs.maxText = elRefs.wrap.select(cl(MAX_SEL));

          var Y_TEXT_OFFSET = '1.2em';

          var step = elRefs.stepsGroup
            .selectAll(cl(STEP_SEL))
            .data(_.identity);

          step.enter().append('rect')
            .attr('class', STEP_SEL)
            .attr('width', STEP_WIDTH)
            .attr('height', 11)
            .attr('x', function (d, i) {
              return i * (STEP_WIDTH);
            })
            .attr('fill', function (d) {
              return legendScale(d);
            });

          elRefs.minText.text('Min: ' + formatter(domain[0]));
          elRefs.maxText.text('Max: ' + formatter(domain[1]));

          var stepsBBox = getBBox(elRefs.stepsGroup);
          var minBBox = getBBox(elRefs.minText);
          var maxBBox = getBBox(elRefs.maxText);

          var minAndStepsWidth = minBBox.width + stepsBBox.width + (TEXT_PADDING * 2);

          var legendWidth = minAndStepsWidth + maxBBox.width;

          chart.requestID = raf.requestAnimationFrame(function () {
            elRefs.stepsGroup
              .attr('transform', translator(minBBox.width + TEXT_PADDING, (availableHeight - 10) / 2 ));

            elRefs.minText
              .attr('dy', Y_TEXT_OFFSET);

            elRefs.maxText
              .attr('x', minAndStepsWidth)
              .attr('dy', Y_TEXT_OFFSET);

            if (chart.rightAlign())
              elRefs.wrap.attr('transform', translator(availableWidth - legendWidth, margin.top));
            else
              elRefs.wrap.attr('transform', translator(margin.left, margin.top));
          });

          chart.destroy = function destroy () {
            if(chart.requestID)
              raf.cancelAnimationFrame(chart.requestID);

            elRefs.container.remove();
            elRefs = null;
          };
        });
      }

      return chart;
    };
  }
}());
