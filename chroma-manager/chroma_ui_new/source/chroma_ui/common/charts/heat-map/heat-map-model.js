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


angular.module('charts').factory('heatMapModelFactory', ['d3', 'chartParamMixins', heatMapModelFactory]);


function heatMapModelFactory (d3, chartParamMixins) {
  'use strict';

  var MODEL_SEL = 'heat-map-model',
    ROW_SEL = 'row',
    CELL_SEL = 'cell';

  return function getModel() {
    var config = {
      x: d3.scale.linear(),
      y: d3.scale.ordinal(),
      z: d3.scale.linear().interpolate(d3.interpolateRgb),
      width: 960,
      height: 400,
      showXAxis: true,
      showYAxis: true,
      showLegend: true,
      lowColor: '#FFFFFF',
      highColor: '#D9534F',
      margin: {top: 0, right: 0, bottom: 0, left: 0},
      transitionDuration: 250
    };

    chartParamMixins(config, chart);

    function chart (selection) {
      var margin = chart.margin(),
        x = chart.x(),
        y = chart.y(),
        z = chart.z();

      selection.each(function render (data) {
        var container = d3.select(this);
        var availableWidth = (chart.width() || parseInt(container.style('width'), 10)) - margin.left - margin.right,
          availableHeight = (chart.height() || parseInt(container.style('height'), 10)) - margin.top - margin.bottom;

        var values = _.cloneDeep(_.pluck(data, 'values')),
          keys = _.pluck(data, 'key'),
          mergedValues = d3.merge(values),
          domain = d3.extent(mergedValues, getProp('z')),
          dateExtent = d3.extent(mergedValues, getProp('x'));

        if (values.length === 0)
          return;

        dateExtent[1].setSeconds(dateExtent[1].getSeconds() + 10);

        x.domain(dateExtent).range([0, availableWidth]);

        y.domain(keys).rangePoints([availableHeight, 0], 1.0);

        z.domain(domain).range([chart.lowColor(), chart.highColor()]);

        // data join
        var heatMapModel = container.selectAll(cl(MODEL_SEL))
          .data([data]);

        // Create the structure on enter.
        var heatMapModelEnter = heatMapModel.enter()
          .append('g')
          .attr('class', MODEL_SEL);

        heatMapModelEnter.append('rect')
          .attr('fill', '#DDD')
          .attr('width', availableWidth)
          .attr('height', availableHeight);

        var gridHeight = availableHeight / keys.length;

        var row = heatMapModel
          .selectAll(cl(ROW_SEL)).data(_.identity);

        row.enter()
          .append('g')
          .attr('class', ROW_SEL);

        row.transition().attr('transform', function (d) {
          return translator(0, y(d.key) - (gridHeight / 2));
        });

        row.exit().remove();

        var cell = row.selectAll(cl(CELL_SEL))
          .data(function (d) {
            var cloned = _.cloneDeep(d.values).sort(function (a, b) { return a.x - b.x; }),
              uniq = _.uniq(cloned, true, function (item) { return item.x.valueOf(); });

            return uniq.map(function (value, index) {
              value.xPos = x(value.x);

              value.size = (index === uniq.length - 1 ?
                chart.width() - value.xPos: x(uniq[index + 1].x) - value.xPos);

              if (value.size <= 0)
                console.warn('broken', value.size);

              return value;
            });
          }, getProp('x'));

        cell.enter().append('rect')
          .attr('class', CELL_SEL)
          .attr('fill', function (d) { return z(d.z); });

        cell.transition().attr('x', getProp('xPos'))
          .attr('width', getProp('size'))
          .attr('height', function() { return gridHeight; })
          .attr('fill', function (d) { return z(d.z); });

        cell.exit().remove();
      });
    }

    var getProp = _.curry(function getProp(prop, d) {
      return d[prop];
    });

    return chart;

    function translator(dx, dy) {
      return 'translate(' + dx + ',' + dy + ')';
    }

    function cl(str) {
      return '.' + str;
    }
  };
}