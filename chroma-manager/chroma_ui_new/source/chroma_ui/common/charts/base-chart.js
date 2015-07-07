//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

  angular.module('charts').factory('baseChart', ['nv', 'd3', function (nv, d3) {
    return function merge(overrides) {
      var defaultDirective = {
        restrict: 'E',
        require: '^?fullScreen',
        replace: true,
        scope: {
          chartData: '=',
          options: '='
        },
        templateUrl: 'common/charts/assets/html/chart.html',
        link: function (scope, element, attrs, fullScreenCtrl) {
          if (fullScreenCtrl) fullScreenCtrl.addListener(setChartViewBox);

          var chart,
            svg = d3.select(element.find('svg')[0]);

          chart = config.generateChart(nv).margin({left: 70, bottom: 100, right: 50});

          svg
            .attr('preserveAspectRatio', 'xMinYMid')
            .attr('width', '100%')
            .attr('height', '100%')
            .datum(scope.chartData);

          var debounced = _.debounce(function onWindowResize() {
            scope.$apply(setChartViewBox);
          }, 150);

          angular.element(window).on('resize', debounced);

          if (scope.options && scope.options.setup) scope.options.setup(chart, d3, nv);

          setChartViewBox();

          /**
           * Sets the viewBox of the chart to the current container width and height
           */
          function setChartViewBox() {
            var width = element.width(),
              height = element.height();

            svg.attr('viewBox', '0 0 ' + width + ' ' + height)
              .transition().duration(500)
              .call(chart);
          }

          var deregister = scope.$watch('chartData', function watcher(newVal, oldVal) {
            if (newVal === oldVal) return;

            config.onUpdate(chart, newVal);

            if (!newVal || !newVal.length || !newVal.filter(function(d) { return d.values.length; }).length) {
              svg.append('rect')
                .attr('fill', '#FFF')
                .attr('width', '100%')
                .attr('height', '100%')
                .classed('noDataOverlay', true);
            } else {
              svg.selectAll('.noDataOverlay').remove();
            }

            // Nvd3 likes to put data directly on the object.
            // That ends up triggering another watch.
            // Clone the val so watch only fires once.
            var val = _.cloneDeep(newVal);

            //Pull the state nvd3 stores and push back to our raw val.
            svg.datum().forEach(function iterate(item) {
              var series = _.findWhere(val, {key: item.key});

              if (series != null) {
                Object.keys(item).filter(function (key) {
                  return key !== 'values';
                }).forEach(function iterate (key) {
                  series[key] = item[key];
                });
              }
            });

            svg.datum(val);
            chart.update();
          }, true);

          scope.$on('$destroy', function onDestroy() {
            deregister();

            angular.element(window).off('resize', debounced);

            if (fullScreenCtrl) fullScreenCtrl.removeListener(setChartViewBox);

            if (chart.destroy)
              chart.destroy();

            chart = null;

            svg.remove();
            svg = null;
          });
        }
      };

      var config = {
        directive: defaultDirective,
        generateChart: function () {
          throw new Error('config::generateChart must be overriden!');
        },
        onUpdate: angular.noop
      };

      _.merge(config, overrides);

      return config.directive;
    };
  }]);

}());
