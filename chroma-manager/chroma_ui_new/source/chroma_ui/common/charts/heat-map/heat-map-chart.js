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


angular.module('charts').factory('heatMapChartFactory',
  ['d3', 'nv', 'chartParamMixins', 'chartUtils', 'heatMapLegendFactory', 'heatMapModelFactory', heatMapChartFactory]);


function heatMapChartFactory(d3, nv, chartParamMixins, chartUtils, heatMapLegendFactory, heatMapModelFactory) {
  'use strict';

  return function getChart() {
    var config = {
      xAxis: nv.models.axis(),
      yAxis: nv.models.axis(),
      width: 960,
      height: 400,
      showXAxis: true,
      showYAxis: true,
      showLegend: true,
      formatter: _.identity,
      margin: {top: 30, right: 20, bottom: 50, left: 60},
      transitionDuration: 250
    };

    var heatMapLegend = heatMapLegendFactory();
    var heatMapModel = heatMapModelFactory();

    chartParamMixins(config, chart);

    chart.xAxis()
      .orient('bottom')
      .margin({right: 50})
      .tickPadding(7);

    chart.yAxis()
      .showMaxMin(false)
      .orient('left');


    function chart(selection) {
      var margin = chart.margin(),
        translator = chartUtils.translator;


      selection.each(function render (data) {
        var container = d3.select(this),
          availableWidth = (parseInt(container.style('width'), 10)) - margin.left - margin.right,
          availableHeight = (parseInt(container.style('height'), 10)) - margin.top - margin.bottom;

        chart.update = function update() {
          container.transition().duration(chart.transitionDuration()).call(chart);
        };

        chart.destroy = function destroy () {
          chart.update = null;

          heatMapModel.destroy();
          heatMapLegend.destroy();

          container.remove();
          container = null;
          wrap = null;
          gEnter = null;
          chartGroupGEnter = null;
        };

        var values = _.pluck(data, 'values');

        if (values.length === 0)
          return;

        //------------------------------------------------------------
        // Setup containers and skeleton of chart

        // data join
        var wrap = container.selectAll('g.nv-wrap.nv-heat-map-chart')
            .data([data]);

        // Create the structure on enter.
        var gEnter = wrap.enter()
            .append('g').attr('class', 'nvd3 nv-wrap nv-heat-map-chart');

        var chartGroupGEnter = gEnter.append('g').attr('class', 'chart-group');

        gEnter.append('g').attr('class', 'legend-group');

        chartGroupGEnter.append('g').attr('class', 'nv-x nv-axis');
        chartGroupGEnter.append('g').attr('class', 'nv-y nv-axis');
        chartGroupGEnter.append('g').attr('class', 'heat-map-group');

        // These operate on enter + update.
        var chartGroup = wrap.select('.chart-group')
          .attr('transform', translator(margin.left, margin.top)),
          legendGroup = wrap.select('.legend-group')
            .attr('transform', translator(margin.left, 0)),
          heatMapGroup = wrap.select('.heat-map-group'),
          xAxisGroup = chartGroup.select('.nv-x'),
          yAxisGroup = chartGroup.select('.nv-y');

        //------------------------------------------------------------
        // Legend

        if (chart.showLegend()) {
          heatMapLegend.formatter(chart.formatter());
          heatMapLegend.width(availableWidth);

          legendGroup
            .datum(data)
            .call(heatMapLegend);

          if (margin.top !== heatMapLegend.height()) {
            margin.top = heatMapLegend.height();
            availableHeight = (parseInt(container.style('height'), 10)) - margin.top - margin.bottom;

            chartGroup.attr('transform', translator(0, margin.top));
          }
        }

        //------------------------------------------------------------
        // Setup heatmap

        heatMapModel
          .width(availableWidth)
          .height(availableHeight);

        heatMapGroup
          .datum(data)
          .call(heatMapModel);

        //------------------------------------------------------------
        // Setup Axes

        if (chart.showXAxis()) {
          chart.xAxis()
            .scale(heatMapModel.x())
            .ticks(availableWidth / 100)
            .tickSize(-availableHeight, 0);

          xAxisGroup
            .attr('transform', translator(0, availableHeight));

          xAxisGroup
            .transition()
            .call(chart.xAxis());
        }

        if (chart.showYAxis()) {
          chart.yAxis()
            .scale(heatMapModel.y())
            .ticks(availableHeight / 36)
            .tickSize(-availableWidth, 0);

          yAxisGroup
            .transition()
            .call(chart.yAxis());
        }

        //------------------------------------------------------------
      });
    }

    d3.rebind(chart, heatMapModel, 'onMouseOver', 'onMouseMove', 'onMouseOut', 'onMouseClick');

    chart.options = nv.utils.optionsFunc.bind(chart);

    chart.destroy = _.noop;

    return chart;
  };
}
