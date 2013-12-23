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

  angular.module('charts').factory('heatMapLegendFactory', ['d3', 'nv', 'chartParamMixins', heatMapLegendFactory]);

  function heatMapLegendFactory (d3, nv, chartParamMixins) {
    var TEXT_PADDING = 5,
      SQUARE_SIZE = 10,
      MIN = 0,
      MAX = 100;

    return function getLegend() {
      var config = {
        margin: {top: 5, right: 0, bottom: 5, left: 0},
        width: 200,
        height: 30,
        steps: 5,
        formatter: _.identity,
        lowColor: '#FFFFFF',
        highColor: '#D9534F',
        rightAlign: true,
        legendScale: d3.scale.linear().interpolate(d3.interpolateRgb)
      };

      chartParamMixins(config, chart);

      function chart (selection) {
        var margin = chart.margin(),
          width = chart.width(),
          height = chart.height(),
          formatter = chart.formatter(),
          legendScale = chart.legendScale(),
          steps = chart.steps();

        selection.each(function(data) {
          var container = d3.select(this);

          var values = _.pluck(data, 'values'),
            mergedValues = d3.merge(values),
            domain = d3.extent(mergedValues, function (d) { return d.z; }),
            stepData = _.range(MIN, MAX, (MAX / steps)).concat(MAX);

          legendScale.domain([MIN, MAX]).range([chart.lowColor(), chart.highColor()]);

          var availableWidth = width - margin.left - margin.right,
            availableHeight = height - margin.top - margin.bottom;

          var LEGEND_SEL = 'nv-legend',
            MIN_SEL = 'min',
            STEPS_SEL = 'steps',
            STEP_SEL = 'step',
            MAX_SEL = 'max';

          //data join.
          var wrap = container.selectAll(cl(LEGEND_SEL)).data([stepData]);

          // setup structure on enter.
          var gEnter = wrap.enter().append('g').attr('class', LEGEND_SEL);

          gEnter.append('text').attr('class', MIN_SEL);
          gEnter.append('g').attr('class', STEPS_SEL);
          gEnter.append('text').attr('class', MAX_SEL);

          // These operate on enter + update.
          var minText = wrap.select(cl(MIN_SEL)),
            stepsGroup = wrap.select(cl(STEPS_SEL)),
            maxText = wrap.select(cl(MAX_SEL));

          var Y_TEXT_OFFSET = '1.2em';

          stepsGroup.attr('stroke', '#EEE');

          minText.text('Min: ' + formatter(domain[0]))
            .attr('dy', Y_TEXT_OFFSET);

          var minBBox = getBBox(minText);

          stepsGroup
            .attr('transform', translator(minBBox.width + TEXT_PADDING, (availableHeight - SQUARE_SIZE) / 2 ));

          var step = stepsGroup
            .selectAll(cl(STEP_SEL))
            .data(_.identity);

          step.enter().append('rect')
            .attr('class', STEP_SEL)
            .attr('width', SQUARE_SIZE)
            .attr('height', SQUARE_SIZE)
            .attr('x', function (d, i) {
              return i * (SQUARE_SIZE + 4);
            })
            .attr('fill', function (d) {
              return legendScale(d);
            });

          var stepsBBox = getBBox(stepsGroup);

          maxText.text('Max: ' + formatter(domain[1]));

          var maxBBox = getBBox(maxText);

          var minAndStepsWidth = minBBox.width + stepsBBox.width + (TEXT_PADDING * 2);

          maxText
            .attr('x', minAndStepsWidth)
            .attr('dy', Y_TEXT_OFFSET);

          var legendWidth = minAndStepsWidth + maxBBox.width;

          wrap.attr('transform', translator(margin.left, margin.top));

          if (chart.rightAlign())
            wrap.attr('transform', translator(availableWidth - legendWidth, margin.top));
        });
      }

      function getBBox(selection) {
        return selection.node().getBBox();
      }

      function translator(dx, dy) {
        return 'translate(' + dx + ',' + dy + ')';
      }

      function cl(str) {
        return '.' + str;
      }

      return chart;
    };
  }
}());
